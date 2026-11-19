from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from cuentas.models import Direccion
from pedidos.models import Pedido, EstadoPedido
from pagos.models import Pago
from .models import Envio, EstadoEnvio


class EnvioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="cliente_envio")
        cls.otro = get_user_model().objects.create_user(username="otro_cliente_envio")
        cls.admin = get_user_model().objects.create_superuser(
            username="admin_envio", email="admin@example.com"
        )
        direccion = Direccion.objects.create(
            usuario=cls.usuario,
            calle="Prueba",
            numero="1",
            ciudad="Rosario",
            provincia="Santa Fe",
            codigo_postal="2000",
        )
        estado, _ = EstadoPedido.objects.get_or_create(nombre="Pendiente de pago")
        cls.pedido = Pedido.objects.create(
            usuario=cls.usuario,
            direccion=direccion,
            estado=estado,
            subtotal=100,
            total=100,
        )
        cls.pago = Pago.objects.create(
            pedido=cls.pedido, monto=100, medio_pago="transferencia"
        )

    def aprobar(self):
        Pago.objects.filter(pk=self.pago.pk).update(estado="aprobado")

    def crear_envio(self):
        self.aprobar()
        return Envio.objects.create(
            pedido=self.pedido,
            estado=EstadoEnvio.objects.get(nombre="En preparación"),
            empresa_transporte="Transporte Demo",
            numero_seguimiento="DEMO-123",
        )

    def test_cuatro_estados_iniciales(self):
        self.assertSetEqual(
            set(EstadoEnvio.objects.values_list("nombre", flat=True)),
            set(EstadoEnvio.Nombre.values),
        )

    def test_no_generar_sin_pago_aprobado(self):
        with self.assertRaisesMessage(ValidationError, "pago confirmado"):
            Envio.objects.create(
                pedido=self.pedido,
                estado=EstadoEnvio.objects.get(nombre="En preparación"),
            )
        self.assertFalse(Envio.objects.exists())

    def test_un_envio_por_pedido(self):
        self.crear_envio()
        with self.assertRaises(ValidationError):
            Envio.objects.create(
                pedido=self.pedido,
                estado=EstadoEnvio.objects.get(nombre="En preparación"),
            )

    def test_estados_visibles_en_card_y_detalle(self):
        envio = self.crear_envio()
        self.client.force_login(self.usuario)
        for nombre in EstadoEnvio.Nombre.values:
            envio.estado = EstadoEnvio.objects.get(nombre=nombre)
            envio.save()
            lista = self.client.get(reverse("mis_pedidos"))
            self.assertContains(lista, f"Pedido #{self.pedido.pk}")
            self.assertContains(lista, nombre)
            self.assertContains(lista, "DEMO-123")
            self.assertContains(
                self.client.get(reverse("detalle_pedido", args=[self.pedido.pk])),
                nombre,
            )

    def test_cliente_no_ve_envio_ajeno_ni_admin(self):
        self.crear_envio()
        self.client.force_login(self.otro)
        self.assertNotContains(self.client.get(reverse("mis_pedidos")), "DEMO-123")
        self.assertEqual(
            self.client.get(
                reverse("detalle_pedido", args=[self.pedido.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("admin:envios_envio_add"), {}).status_code, 302
        )
        self.assertEqual(Envio.objects.count(), 1)

    def test_pedido_sin_envio(self):
        self.client.force_login(self.usuario)
        self.assertContains(
            self.client.get(reverse("mis_pedidos")), "Envío aún no generado"
        )
        self.assertContains(
            self.client.get(reverse("detalle_pedido", args=[self.pedido.pk])),
            "Envío aún no generado",
        )

    def datos_admin(self, estado):
        return {
            "pedido": self.pedido.pk,
            "estado": EstadoEnvio.objects.get(nombre=estado).pk,
            "empresa_transporte": "Transporte Demo",
            "numero_seguimiento": "ADMIN-123",
            "costo_envio": "0",
            "fecha_envio_0": "",
            "fecha_envio_1": "",
            "fecha_entrega_0": "",
            "fecha_entrega_1": "",
            "_save": "Guardar",
        }

    def test_admin_crea_y_actualiza_envio(self):
        self.aprobar()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:envios_envio_add"), self.datos_admin("En preparación")
        )
        self.assertEqual(response.status_code, 302)
        envio = Envio.objects.get(pedido=self.pedido)
        response = self.client.post(
            reverse("admin:envios_envio_change", args=[envio.pk]),
            self.datos_admin("En tránsito"),
        )
        self.assertEqual(response.status_code, 302)
        envio.refresh_from_db()
        self.assertEqual(envio.estado.nombre, "En tránsito")
        self.client.force_login(self.usuario)
        self.assertContains(self.client.get(reverse("mis_pedidos")), "En tránsito")

    def test_admin_no_puede_falsificar_pedido_sin_pago(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:envios_envio_add"), self.datos_admin("En preparación")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Envio.objects.exists())

    def test_inline_en_pedido_pagado_y_no_pagado(self):
        self.client.force_login(self.admin)
        ruta = reverse("admin:pedidos_pedido_change", args=[self.pedido.pk])
        self.assertNotContains(self.client.get(ruta), "id_envio-0-estado")
        self.aprobar()
        self.assertContains(self.client.get(ruta), "id_envio-0-estado")

    def test_fecha_entrega_no_anterior_a_envio(self):
        from datetime import timedelta
        from django.utils import timezone

        envio = self.crear_envio()
        envio.fecha_envio = timezone.now()
        envio.fecha_entrega = envio.fecha_envio - timedelta(days=1)
        with self.assertRaises(ValidationError):
            envio.save()

    def test_crear_desde_inline_del_pedido(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from .admin import EnvioInline

        self.aprobar()
        request = RequestFactory().post("/admin/")
        request.user = self.admin
        inline = EnvioInline(Pedido, AdminSite())
        datos = {
            "envio-TOTAL_FORMS": "1",
            "envio-INITIAL_FORMS": "0",
            "envio-MIN_NUM_FORMS": "0",
            "envio-MAX_NUM_FORMS": "1",
            "envio-0-pedido": self.pedido.pk,
            "envio-0-estado": EstadoEnvio.objects.get(nombre="En preparación").pk,
            "envio-0-costo_envio": "0",
        }
        formset = inline.get_formset(request, self.pedido)(
            data=datos, instance=self.pedido, prefix="envio"
        )
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.assertTrue(Envio.objects.filter(pedido=self.pedido).exists())
