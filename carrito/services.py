from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from productos.models import Producto
from .models import Carrito, ItemCarrito


@transaction.atomic
def agregar_producto(usuario, producto_id, cantidad=1):

    # Validar cantidad
    if cantidad < 1:
        raise ValidationError("La cantidad debe ser mayor a cero.")

    # Buscar producto
    producto = get_object_or_404(Producto, pk=producto_id)

    # Comprobar disponibilidad
    if not producto.activo:
        raise ValidationError("El producto no estÃ¡ disponible.")

    # Obtener o crear carrito
    carrito, creado = Carrito.objects.get_or_create(usuario=usuario)

    carrito = Carrito.objects.select_for_update().get(pk=carrito.pk)

    # Buscar el producto dentro del carrito
    item, creado = ItemCarrito.objects.get_or_create(
        carrito=carrito, producto=producto, defaults={"cantidad": cantidad}
    )

    # Determinar nueva cantidad
    if creado:
        nueva_cantidad = cantidad
    else:
        nueva_cantidad = item.cantidad + cantidad

    # Comprobar stock
    if nueva_cantidad > producto.stock:
        raise ValidationError("Stock insuficiente.")

    # Guardar cambios
    item.cantidad = nueva_cantidad
    item.save()

    return item
