from django.db import models

from django.db import models
from django.conf import settings


class Perfil(models.Model):

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil"
    )

    telefono = models.CharField(
        max_length=30,
        blank=True
    )

    def __str__(self):
        return self.usuario.username


class Direccion(models.Model):

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="direcciones"
    )

    calle = models.CharField(max_length=150)

    numero = models.CharField(max_length=20)

    piso = models.CharField(
        max_length=20,
        blank=True
    )

    departamento = models.CharField(
        max_length=20,
        blank=True
    )

    ciudad = models.CharField(max_length=100)

    provincia = models.CharField(max_length=100)

    codigo_postal = models.CharField(max_length=20)

    predeterminada = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.calle} {self.numero} - {self.ciudad}"