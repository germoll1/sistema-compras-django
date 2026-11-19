from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from productos.models import Producto, Categoria
from carrito.services import agregar_producto
from carrito.models import Carrito
from pagos.models import Pago
from .models import Pedido


class CompraTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="comprador", password="UnaClave123!"
        )
        self.other = get_user_model().objects.create_user(
            username="otro", password="UnaClave123!"
        )
        self.cat = Categoria.objects.create(nombre="Tecnología")
        self.producto = Producto.objects.create(
            nombre="Teclado", categoria=self.cat, precio="1500", stock=3
        )
        self.datos = dict(
            calle="Demo",
            numero="123",
            ciudad="Rosario",
            provincia="Santa Fe",
            codigo_postal="2000",
            medio_pago="transferencia",
        )
        self.client.force_login(self.user)

    def comprar(self):
        agregar_producto(self.user, self.producto.pk)
        return self.client.post(reverse("checkout"), self.datos)

    def test_rutas_exigen_login(self):
        self.client.logout()
        for ruta in [
            "inicio",
            "listado_productos",
            "listado_categorias",
            "ver_carrito",
            "checkout",
            "mis_pedidos",
        ]:
            self.assertRedirects(
                self.client.get(reverse(ruta)),
                reverse("login") + "?next=" + reverse(ruta),
                fetch_redirect_response=False,
            )

    def test_compra_atomica_y_sin_duplicados(self):
        self.comprar()
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.total, Decimal("1500"))
        self.assertEqual(pedido.pagos.get().estado, "pendiente")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)
        self.assertFalse(self.user.carrito.items.exists())
        self.client.post(reverse("checkout"), self.datos)
        self.assertEqual(Pedido.objects.count(), 1)
        detalle = self.client.get(reverse("detalle_pedido", args=[pedido.pk]))
        self.assertContains(detalle, "TIENDA.DEMO.COMPRAS")
        self.assertContains(detalle, "comprobantes@tienda.example")

    def test_no_ver_pedido_ni_pagar_pedido_ajeno(self):
        self.comprar()
        pedido = Pedido.objects.get()
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("detalle_pedido", args=[pedido.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("iniciar_pago", args=[pedido.pk])).status_code, 404
        )
        self.assertNotContains(
            self.client.get(reverse("mis_pedidos")), f"Pedido #{pedido.pk}"
        )
        self.assertNotContains(
            self.client.get(reverse("ver_carrito")), self.producto.nombre
        )

    def test_stock_insuficiente_no_crea_pedido(self):
        agregar_producto(self.user, self.producto.pk)
        self.producto.stock = 0
        self.producto.save()
        self.assertContains(
            self.client.post(reverse("checkout"), self.datos), "disponibilidad"
        )
        self.assertFalse(Pedido.objects.exists())
        self.assertEqual(self.user.carrito.items.count(), 1)

    def test_catalogo_filtra_categoria_y_csrf(self):
        otra = Categoria.objects.create(nombre="Otra")
        Producto.objects.create(nombre="No visible", categoria=otra, precio=1, stock=2)
        respuesta = self.client.get(
            reverse("listado_productos"), {"categoria": self.cat.pk}
        )
        self.assertContains(respuesta, "Teclado")
        self.assertNotContains(respuesta, "No visible")
        self.assertContains(respuesta, "csrfmiddlewaretoken")
        self.assertEqual(
            self.client.post(
                reverse("agregar_al_carrito", args=[self.producto.pk])
            ).json()["cantidad"],
            1,
        )

    def test_mercadopago_sin_claves_no_vacia_carrito(self):
        agregar_producto(self.user, self.producto.pk)
        with override_settings(MERCADOPAGO_ACCESS_TOKEN=""):
            self.datos["medio_pago"] = "mercadopago"
            self.assertContains(
                self.client.post(reverse("checkout"), self.datos), "no está configurado"
            )
        self.assertFalse(Pedido.objects.exists())

    def test_webhook_rechaza_firma_invalida(self):
        self.assertEqual(
            self.client.post(reverse("mercadopago_webhook")).status_code, 403
        )

    @override_settings(MERCADOPAGO_WEBHOOK_SECRET="secreto")
    def test_webhook_verifica_api_y_monto_idempotente(self):
        import hashlib, hmac

        self.comprar()
        pago = Pago.objects.get()
        pago.medio_pago = "mercadopago"
        pago.save()
        firma = hmac.new(
            b"secreto", b"id:123;request-id:abc;ts:12345;", hashlib.sha256
        ).hexdigest()
        ruta = reverse("mercadopago_webhook") + "?data.id=123"
        headers = {
            "HTTP_X_SIGNATURE": "ts=12345,v1=" + firma,
            "HTTP_X_REQUEST_ID": "abc",
        }
        data = {
            "id": 123,
            "external_reference": str(pago.pedido_id),
            "transaction_amount": 1,
            "currency_id": "ARS",
            "status": "approved",
        }
        with patch("pagos.views.api", return_value=data):
            self.assertEqual(self.client.post(ruta, **headers).status_code, 400)
            data["transaction_amount"] = 1500
            self.assertEqual(self.client.post(ruta, **headers).status_code, 200)
            self.assertEqual(self.client.post(ruta, **headers).status_code, 200)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, "aprobado")
        self.assertEqual(Pago.objects.count(), 1)
        self.assertEqual(pago.pedido.estado.nombre, "Pago confirmado")

    def test_csrf_obligatorio_y_post_obligatorio(self):
        from django.test import Client

        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.user)
        ruta = reverse("agregar_al_carrito", args=[self.producto.pk])
        self.assertEqual(cliente.post(ruta).status_code, 403)
        self.assertEqual(cliente.get(ruta).status_code, 405)
        cliente.get(reverse("listado_productos"))
        self.assertEqual(
            cliente.post(
                ruta, HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value
            ).status_code,
            200,
        )

    def test_confirmacion_admin_reflejada_en_compra(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from pagos.admin import PagoAdmin

        self.comprar()
        request = RequestFactory().post("/admin/")
        request.user = get_user_model().objects.create_superuser(
            "administrador", "admin@example.com", "OtraClave123!"
        )
        administrador = PagoAdmin(Pago, AdminSite())
        with patch.object(administrador, "message_user"):
            administrador.confirmar_transferencias(request, Pago.objects.all())
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.estado.nombre, "Pago confirmado")
        self.assertContains(
            self.client.get(reverse("detalle_pedido", args=[pedido.pk])),
            "Pago confirmado",
        )

    @override_settings(
        MERCADOPAGO_ACCESS_TOKEN="test",
        MERCADOPAGO_WEBHOOK_SECRET="secret",
        PUBLIC_BASE_URL="https://tienda.example",
        MERCADOPAGO_SANDBOX=True,
    )
    def test_preferencia_mp_y_retorno_no_confirman_pago(self):
        self.datos["medio_pago"] = "mercadopago"
        self.comprar()
        pedido = Pedido.objects.get()
        with patch(
            "pagos.views.api",
            return_value={
                "id": "preference123",
                "sandbox_init_point": "https://sandbox.mercadopago.com.ar/checkout/test",
            },
        ) as api:
            respuesta = self.client.post(reverse("iniciar_pago", args=[pedido.pk]))
            self.assertEqual(
                respuesta.url, "https://sandbox.mercadopago.com.ar/checkout/test"
            )
            self.assertEqual(
                api.call_args.args[1]["external_reference"], str(pedido.pk)
            )
            self.assertEqual(api.call_args.args[1]["items"][0]["unit_price"], 1500)
        self.client.get(
            reverse("detalle_pedido", args=[pedido.pk]),
            {"status": "approved", "payment_id": "123"},
        )
        self.assertEqual(Pago.objects.get().estado, "pendiente")

    def test_formularios_y_admin_accesibles(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertContains(self.client.get(reverse("registro")), "Correo electrónico")
        self.assertEqual(self.client.get("/admin/login/").status_code, 200)

    def test_eliminar_solo_item_propio(self):
        propio = agregar_producto(self.user, self.producto.pk)
        ajeno = agregar_producto(self.other, self.producto.pk)
        ruta_ajena = reverse("eliminar_del_carrito", args=[ajeno.pk])
        self.assertEqual(self.client.post(ruta_ajena).status_code, 404)
        self.assertTrue(self.other.carrito.items.filter(pk=ajeno.pk).exists())
        ruta = reverse("eliminar_del_carrito", args=[propio.pk])
        self.assertEqual(self.client.get(ruta).status_code, 405)
        self.assertRedirects(self.client.post(ruta), reverse("ver_carrito"))
        self.assertFalse(self.user.carrito.items.exists())

    def test_login_bienvenida_y_navegacion(self):
        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {"username": "comprador", "password": "UnaClave123!"},
            follow=True,
        )
        self.assertContains(response, "Bienvenido a nuestra tienda virtual")
        self.assertContains(response, "Cerrar sesión")
        self.assertNotContains(response, "← Volver")
        self.assertContains(response, "css/styles.css")
