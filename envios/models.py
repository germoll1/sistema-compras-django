from django.db import models
from django.db.models import Q
from pedidos.models import Pedido


class EstadoEnvio(models.Model):

    nombre = models.CharField(
        max_length=50,
        unique=True
    )

    def __str__(self):
        return self.nombre


class Envio(models.Model):

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.PROTECT,
        related_name="envio"
    )

    estado = models.ForeignKey(
        EstadoEnvio,
        on_delete=models.PROTECT
    )

    empresa_transporte = models.CharField(
        max_length=100,
        blank=True
    )

    numero_seguimiento = models.CharField(
        max_length=100,
        blank=True
    )

    fecha_envio = models.DateTimeField(
        null=True,
        blank=True
    )

    fecha_entrega = models.DateTimeField(
        null=True,
        blank=True
    )

    costo_envio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(costo_envio__gte=0),
                name="envio_costo_no_negativo"
            )
        ]

    def __str__(self):
        return f"Envío del pedido #{self.pedido_id}"