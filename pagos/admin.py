from django.contrib import admin, messages
from django.db import transaction
from pedidos.models import EstadoPedido
from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "monto", "medio_pago", "estado", "fecha")
    list_filter = ("estado", "medio_pago")
    search_fields = ("pedido__id", "pedido__usuario__username")
    readonly_fields = (
        "pedido",
        "monto",
        "medio_pago",
        "estado",
        "referencia_externa",
        "fecha",
    )
    actions = ["confirmar_transferencias"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(
        description="Confirmar transferencias seleccionadas (comprobante verificado)",
        permissions=["change"],
    )
    def confirmar_transferencias(self, request, queryset):
        with transaction.atomic():
            estado, _ = EstadoPedido.objects.get_or_create(nombre="Pago confirmado")
            cantidad = 0
            for pago in queryset.select_for_update().filter(
                medio_pago="transferencia", estado="pendiente"
            ):
                pago.estado = "aprobado"
                pago.save(update_fields=["estado"])
                pago.pedido.estado = estado
                pago.pedido.save(update_fields=["estado"])
                cantidad += 1
        self.message_user(
            request, f"{cantidad} transferencia(s) confirmada(s).", messages.SUCCESS
        )
