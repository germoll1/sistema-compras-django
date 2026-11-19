from django.contrib import admin
from pagos.models import Pago
from envios.admin import EnvioInline
from .models import Pedido, DetallePedido, EstadoPedido


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ("producto", "cantidad", "precio_unitario", "subtotal")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    readonly_fields = ("monto", "medio_pago", "estado", "referencia_externa", "fecha")
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "estado", "fecha", "total")
    list_filter = ("estado", "fecha")
    search_fields = ("=id", "usuario__username")
    readonly_fields = (
        "usuario",
        "direccion",
        "fecha",
        "subtotal",
        "costo_envio",
        "total",
        "direccion_entrega",
    )
    inlines = [DetallePedidoInline, PagoInline, EnvioInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EstadoPedido)
class EstadoPedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
