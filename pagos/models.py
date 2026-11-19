from django.db import models
from django.db.models import Q
from pedidos.models import Pedido


class Pago(models.Model):

    class MedioPago(models.TextChoices):
        MERCADOPAGO = "mercadopago", "Mercado Pago"
        TARJETA = "tarjeta", "Tarjeta"
        TRANSFERENCIA = "transferencia", "Transferencia"
        EFECTIVO = "efectivo", "Efectivo"

    class EstadoPago(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        REEMBOLSADO = "reembolsado", "Reembolsado"

    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="pagos")

    fecha = models.DateTimeField(auto_now_add=True)

    monto = models.DecimalField(max_digits=12, decimal_places=2)

    medio_pago = models.CharField(max_length=30, choices=MedioPago.choices)

    estado = models.CharField(
        max_length=30, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE
    )

    referencia_externa = models.CharField(max_length=150, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(monto__gt=0), name="pago_monto_positivo")
        ]

    def __str__(self):
        return f"Pago #{self.pk} - {self.estado}"
