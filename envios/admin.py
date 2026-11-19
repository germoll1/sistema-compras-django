from django import forms
from django.contrib import admin
from django.db.models import F
from pedidos.models import Pedido
from .models import Envio, EstadoEnvio


class EnvioForm(forms.ModelForm):
    class Meta:
        model = Envio
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"].queryset = EstadoEnvio.objects.filter(
            nombre__in=EstadoEnvio.Nombre.values
        )
        self.fields["estado"].empty_label = None
        if not self.instance.pk:
            self.initial["estado"] = (
                EstadoEnvio.objects.filter(nombre=EstadoEnvio.Nombre.PREPARACION)
                .values_list("pk", flat=True)
                .first()
            )
        if "pedido" in self.fields:
            self.fields["pedido"].queryset = Pedido.objects.filter(
                pagos__estado="aprobado",
                pagos__monto__gte=F("total"),
                envio__isnull=True,
            ).distinct()
            self.fields["pedido"].help_text = (
                "Solo aparecen compras con pago confirmado y sin un envío previo."
            )
        self.fields["costo_envio"].help_text = (
            "Registro logístico; no modifica el importe ya pagado por el cliente."
        )


@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    form = EnvioForm
    list_display = (
        "id",
        "pedido",
        "estado",
        "empresa_transporte",
        "numero_seguimiento",
        "fecha_envio",
    )
    list_filter = ("estado", "empresa_transporte")
    search_fields = ("=pedido__id", "pedido__usuario__username", "numero_seguimiento")
    list_select_related = ("pedido", "estado")

    def get_readonly_fields(self, request, obj=None):
        return ("pedido",) if obj else ()

    def has_delete_permission(self, request, obj=None):
        return False


class EnvioInlineForm(EnvioForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            # Elegir un estado marca el formulario extra como una creación explícita.
            self.initial.pop("estado", None)
            self.fields["estado"].empty_label = (
                "Seleccioná un estado para generar el envío"
            )


class EnvioInline(admin.StackedInline):
    model = Envio
    form = EnvioInlineForm
    max_num = 1
    extra = 1
    can_delete = False
    show_change_link = True

    def get_extra(self, request, obj=None, **kwargs):
        return 1 if self.has_add_permission(request, obj) else 0

    def has_add_permission(self, request, obj=None):
        return bool(
            obj
            and obj.pagos.filter(estado="aprobado", monto__gte=obj.total).exists()
            and not Envio.objects.filter(pedido=obj).exists()
            and super().has_add_permission(request, obj)
        )


@admin.register(EstadoEnvio)
class EstadoEnvioAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
