from django.urls import path
from . import views

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("", views.mis_pedidos, name="mis_pedidos"),
    path("<int:pedido_id>/", views.detalle_pedido, name="detalle_pedido"),
]
