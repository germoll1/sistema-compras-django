from django.db import models

from django.db import models
from django.conf import settings
from productos.models import Producto


class Carrito(models.Model):

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carrito"
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Carrito de {self.usuario.username}"


class ItemCarrito(models.Model):

    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE,
        related_name="items"
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="items_carrito"
    )

    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["carrito", "producto"],
                name="unique_producto_carrito"
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=1),
                name="cantidad_carrito_positiva"
            )
        ]

    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad}"
