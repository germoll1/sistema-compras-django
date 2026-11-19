from django.db import models
from django.conf import settings
from productos.models import Producto
from cuentas.models import Direccion


class EstadoPedido(models.Model):
    nombre = models.CharField(
        max_length=50,
        unique=True
    )

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos"
    )

    direccion = models.ForeignKey(
        Direccion,
        on_delete=models.PROTECT,
        related_name="pedidos"
    )

    estado = models.ForeignKey(
        EstadoPedido,
        on_delete=models.PROTECT
    )

    fecha = models.DateTimeField(auto_now_add=True)

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    costo_envio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Copia histórica de la dirección al comprar
    direccion_entrega = models.JSONField(default=dict)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles"
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_pedido"
    )

    cantidad = models.PositiveIntegerField()

    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=1),
                name="cantidad_detalle_positiva"
            ),
            models.UniqueConstraint(
                fields=["pedido", "producto"],
                name="producto_unico_por_pedido"
            )
        ]

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"