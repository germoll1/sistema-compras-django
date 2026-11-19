

from django.urls import path
from . import views

urlpatterns = [
    path("", views.listado_productos, name="listado_productos"),
    path("categorias/", views.listado_categorias, name="listado_categorias"),
]