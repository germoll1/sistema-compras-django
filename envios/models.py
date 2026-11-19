from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from pedidos.models import Pedido


class EstadoEnvio(models.Model):
    class Nombre(models.TextChoices):
        PREPARACION = "En preparación", "En preparación"
        TRANSITO = "En tránsito", "En tránsito"
        PENDIENTE = "Pendiente de entrega", "Pendiente de entrega"
        ENTREGADO = "Entregado", "Entregado"

    nombre = models.CharField(max_length=50, unique=True, choices=Nombre.choices)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    nombre__in=[
                        "En preparación",
                        "En tránsito",
                        "Pendiente de entrega",
                        "Entregado",
                    ]
                ),
                name="estado_envio_permitido",
            )
        ]

    def __str__(self):
        return self.nombre


class Envio(models.Model):
    pedido = models.OneToOneField(
        Pedido, on_delete=models.PROTECT, related_name="envio"
    )
    estado = models.ForeignKey(EstadoEnvio, on_delete=models.PROTECT)
    empresa_transporte = models.CharField(
        "Empresa de transporte", max_length=100, blank=True
    )
    numero_seguimiento = models.CharField(
        "Número de seguimiento", max_length=100, blank=True
    )
    fecha_envio = models.DateTimeField("Fecha de envío", null=True, blank=True)
    fecha_entrega = models.DateTimeField("Fecha de entrega", null=True, blank=True)
    costo_envio = models.DecimalField(
        "Costo de envío", max_digits=12, decimal_places=2, default=0
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(costo_envio__gte=0), name="envio_costo_no_negativo"
            )
        ]

    @property
    def clase_estado(self):
        return {
            EstadoEnvio.Nombre.PREPARACION: "preparacion",
            EstadoEnvio.Nombre.TRANSITO: "transito",
            EstadoEnvio.Nombre.PENDIENTE: "pendiente",
            EstadoEnvio.Nombre.ENTREGADO: "entregado",
        }.get(self.estado.nombre, "preparacion")

    def clean(self):
        super().clean()
        if self.pedido_id:
            anterior = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("pedido_id", flat=True)
                .first()
                if self.pk
                else None
            )
            if (
                anterior != self.pedido_id
                and not self.pedido.pagos.filter(
                    estado="aprobado", monto__gte=self.pedido.total
                ).exists()
            ):
                raise ValidationError(
                    "Solo se puede generar un envío para una compra con el pago confirmado."
                )
        if (
            self.fecha_envio
            and self.fecha_entrega
            and self.fecha_entrega < self.fecha_envio
        ):
            raise ValidationError(
                {"fecha_entrega": "La entrega no puede ser anterior al envío."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Envío del pedido #{self.pedido_id}"
