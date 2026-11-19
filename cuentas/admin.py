from django.contrib import admin

from django.contrib import admin
from .models import Perfil, Direccion


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "telefono"
    )


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "calle",
        "numero",
        "ciudad",
        "predeterminada"
    )

    list_filter = ("provincia", "predeterminada")

    search_fields = (
        "usuario__username",
        "calle",
        "ciudad"
    )