from django.contrib import admin
from .models import Envio, EstadoEnvio


@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido",
        "estado",
        "empresa_transporte",
        "fecha_envio"
    )


@admin.register(EstadoEnvio)
class EstadoEnvioAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")