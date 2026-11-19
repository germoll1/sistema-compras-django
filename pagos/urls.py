from django.urls import path
from . import views

urlpatterns = [
    path(
        "mercadopago/notificaciones/",
        views.mercadopago_webhook,
        name="mercadopago_webhook",
    ),
    path("<int:pedido_id>/mercadopago/", views.iniciar_pago, name="iniciar_pago"),
]
