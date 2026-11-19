from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from carrito.models import Carrito
from productos.models import Producto
from pagos.models import Pago
from .models import Pedido, DetallePedido, EstadoPedido
from .forms import CheckoutForm


@login_required
def checkout(request):
    form = CheckoutForm(request.POST or None)
    carrito = Carrito.objects.filter(usuario=request.user).first()
    items = list(carrito.items.select_related("producto")) if carrito else []
    total = sum((i.producto.precio * i.cantidad for i in items), Decimal("0"))
    if not items:
        messages.info(request, "Tu carrito está vacío.")
        return redirect("ver_carrito")
    if request.method == "POST" and form.is_valid():
        try:
            if form.cleaned_data["medio_pago"] == "mercadopago" and not (
                settings.MERCADOPAGO_ACCESS_TOKEN
                and settings.MERCADOPAGO_WEBHOOK_SECRET
                and settings.PUBLIC_BASE_URL.startswith("https://")
            ):
                raise ValidationError(
                    "Mercado Pago todavía no está configurado. Podés elegir transferencia."
                )
            with transaction.atomic():
                carrito = Carrito.objects.select_for_update().get(
                    pk=carrito.pk, usuario=request.user
                )
                items = list(
                    carrito.items.select_for_update()
                    .select_related("producto")
                    .order_by("producto_id")
                )
                if not items:
                    raise ValidationError("El carrito ya fue procesado.")
                productos = {
                    x.pk: x
                    for x in Producto.objects.select_for_update()
                    .filter(pk__in=[i.producto_id for i in items])
                    .order_by("pk")
                }
                total = Decimal("0")
                for item in items:
                    prod = productos[item.producto_id]
                    if (
                        not prod.activo
                        or prod.stock < item.cantidad
                        or prod.precio <= 0
                    ):
                        raise ValidationError(
                            f"Verificá la disponibilidad de {prod.nombre}."
                        )
                    total += prod.precio * item.cantidad
                direccion = form.save(commit=False)
                direccion.usuario = request.user
                direccion.save()
                estado, _ = EstadoPedido.objects.get_or_create(
                    nombre="Pendiente de pago"
                )
                pedido = Pedido.objects.create(
                    usuario=request.user,
                    direccion=direccion,
                    estado=estado,
                    subtotal=total,
                    total=total,
                    direccion_entrega={
                        campo: getattr(direccion, campo) for campo in form.Meta.fields
                    },
                )
                for item in items:
                    prod = productos[item.producto_id]
                    DetallePedido.objects.create(
                        pedido=pedido,
                        producto=prod,
                        cantidad=item.cantidad,
                        precio_unitario=prod.precio,
                        subtotal=prod.precio * item.cantidad,
                    )
                    prod.stock -= item.cantidad
                    prod.save(update_fields=["stock"])
                Pago.objects.create(
                    pedido=pedido,
                    monto=total,
                    medio_pago=form.cleaned_data["medio_pago"],
                )
                carrito.items.all().delete()
            return redirect("detalle_pedido", pedido_id=pedido.pk)
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
    return render(
        request, "carrito/checkout.html", {"form": form, "items": items, "total": total}
    )


@login_required
def mis_pedidos(request):
    return render(
        request,
        "carrito/pedidos.html",
        {
            "pedidos": Pedido.objects.filter(usuario=request.user)
            .select_related("estado", "envio__estado")
            .order_by("-fecha")
        },
    )


@login_required
def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(
        Pedido.objects.select_related("estado", "envio__estado"),
        pk=pedido_id,
        usuario=request.user,
    )
    return render(
        request,
        "carrito/pedido.html",
        {
            "pedido": pedido,
            "pago": pedido.pagos.order_by("-pk").first(),
            "alias": settings.TRANSFERENCIA_ALIAS,
            "email_comprobante": settings.TRANSFERENCIA_EMAIL,
        },
    )
