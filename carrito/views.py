from django.shortcuts import render

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from productos.models import Producto
from .models import Carrito, ItemCarrito
from .services import agregar_producto


@login_required
@require_POST
def agregar_al_carrito(request, producto_id):

    producto = get_object_or_404(Producto, pk=producto_id)

    try:
        item = agregar_producto(
            usuario=request.user, producto_id=producto.pk, cantidad=1
        )

        return JsonResponse(
            {
                "ok": True,
                "mensaje": "Producto agregado al carrito",
                "producto": producto.nombre,
                "cantidad": item.cantidad,
            }
        )

    except ValidationError as error:
        return JsonResponse({"ok": False, "error": error.messages[0]}, status=400)


@login_required
def ver_carrito(request):

    carrito = Carrito.objects.filter(usuario=request.user).first()

    items_carrito = []
    total = Decimal("0.00")

    if carrito:
        items = carrito.items.select_related("producto")

        for item in items:
            subtotal = item.producto.precio * item.cantidad

            items_carrito.append(
                {
                    "id": item.pk,
                    "producto": item.producto,
                    "cantidad": item.cantidad,
                    "subtotal": subtotal,
                }
            )

            total += subtotal

    contexto = {"items_carrito": items_carrito, "total": total}

    return render(request, "carrito/detalle.html", contexto)


from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect


@login_required
@require_POST
def eliminar_del_carrito(request, item_id):
    with transaction.atomic():
        carrito = get_object_or_404(
            Carrito.objects.select_for_update(), usuario=request.user
        )
        item = get_object_or_404(ItemCarrito, pk=item_id, carrito=carrito)
        item.delete()
    messages.success(request, "Producto eliminado del carrito.")
    return redirect("ver_carrito")
