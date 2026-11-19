import hashlib
import hmac
import json
import logging
from decimal import Decimal
from urllib.request import Request, urlopen
from urllib.error import URLError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from pedidos.models import EstadoPedido
from .models import Pago

logger = logging.getLogger(__name__)


def api(path, payload=None):
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        raise ValueError("Mercado Pago no configurado")
    req = Request(
        "https://api.mercadopago.com" + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": "Bearer " + settings.MERCADOPAGO_ACCESS_TOKEN,
            "Content-Type": "application/json",
        },
    )
    with urlopen(req, timeout=20) as response:
        return json.load(response)


@login_required
@require_POST
def iniciar_pago(request, pedido_id):
    pago = get_object_or_404(
        Pago.objects.select_related("pedido"),
        pedido_id=pedido_id,
        pedido__usuario=request.user,
        medio_pago="mercadopago",
    )
    if pago.estado == Pago.EstadoPago.APROBADO:
        return redirect("detalle_pedido", pedido_id=pedido_id)
    base = settings.PUBLIC_BASE_URL
    if not base.startswith("https://") or not settings.MERCADOPAGO_WEBHOOK_SECRET:
        messages.error(request, "Mercado Pago todavía no está configurado.")
        return redirect("detalle_pedido", pedido_id=pedido_id)
    try:
        # One reusable preference per order; the cart is already converted to an order.
        with transaction.atomic():
            pago = (
                Pago.objects.select_for_update()
                .select_related("pedido")
                .get(pk=pago.pk)
            )
            if pago.referencia_externa:
                preference = api("/checkout/preferences/" + pago.referencia_externa)
            else:
                retorno = base + reverse("detalle_pedido", args=[pedido_id])
                preference = api(
                    "/checkout/preferences",
                    {
                        "items": [
                            {
                                "id": str(pedido_id),
                                "title": f"Pedido #{pedido_id}",
                                "quantity": 1,
                                "currency_id": "ARS",
                                "unit_price": float(pago.monto),
                            }
                        ],
                        "external_reference": str(pedido_id),
                        "back_urls": {
                            "success": retorno,
                            "pending": retorno,
                            "failure": retorno,
                        },
                        "auto_return": "approved",
                        "notification_url": base + reverse("mercadopago_webhook"),
                    },
                )
                pago.referencia_externa = preference["id"]
                pago.save(update_fields=["referencia_externa"])
            url = preference[
                "sandbox_init_point" if settings.MERCADOPAGO_SANDBOX else "init_point"
            ]
        return redirect(url)
    except (URLError, ValueError, KeyError, TimeoutError):
        logger.exception("No se pudo iniciar Mercado Pago para pedido %s", pedido_id)
        messages.error(
            request,
            "No pudimos conectar con Mercado Pago. Tu pedido está guardado; intentá nuevamente.",
        )
        return redirect("detalle_pedido", pedido_id=pedido_id)


@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET
    payment_id = request.GET.get("data.id", "")
    request_id = request.headers.get("x-request-id", "")
    try:
        signature = dict(
            part.strip().split("=", 1)
            for part in request.headers.get("x-signature", "").split(",")
        )
        ts, digest = signature["ts"], signature["v1"]
        if not (secret and payment_id.isdigit() and request_id and ts.isdigit()):
            raise ValueError()
        manifest = f"id:{payment_id.lower()};request-id:{request_id};ts:{ts};"
        expected = hmac.new(
            secret.encode(), manifest.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, digest):
            raise ValueError()
    except (ValueError, KeyError):
        return JsonResponse({"error": "Firma inválida"}, status=403)
    try:
        data = api("/v1/payments/" + payment_id)
        if str(data.get("id")) != payment_id:
            raise ValueError()
        with transaction.atomic():
            pago = (
                Pago.objects.select_for_update()
                .select_related("pedido")
                .get(pedido_id=data.get("external_reference"), medio_pago="mercadopago")
            )
            if (
                Decimal(str(data["transaction_amount"])) != pago.monto
                or data.get("currency_id") != "ARS"
            ):
                return JsonResponse({"error": "Monto o moneda incorrectos"}, status=400)
            estados = {
                "approved": "aprobado",
                "rejected": "rechazado",
                "refunded": "reembolsado",
                "charged_back": "reembolsado",
                "pending": "pendiente",
                "in_process": "pendiente",
                "cancelled": "rechazado",
            }
            nuevo = estados.get(data.get("status"))
            # Older pending/rejected notifications must not undo a verified approval.
            if (
                nuevo
                and pago.estado != "reembolsado"
                and not (
                    pago.estado == "aprobado" and nuevo in ("pendiente", "rechazado")
                )
            ):
                pago.estado = nuevo
                pago.save(update_fields=["estado"])
                nombre = {
                    "aprobado": "Pago confirmado",
                    "reembolsado": "Pago reembolsado",
                    "rechazado": "Pago rechazado",
                    "pendiente": "Pendiente de pago",
                }[nuevo]
                estado, _ = EstadoPedido.objects.get_or_create(nombre=nombre)
                pago.pedido.estado = estado
                pago.pedido.save(update_fields=["estado"])
        return JsonResponse({"ok": True})
    except Pago.DoesNotExist:
        return JsonResponse({"error": "Pedido desconocido"}, status=404)
    except (URLError, ValueError, KeyError, TypeError, TimeoutError):
        logger.exception("No se pudo verificar pago %s", payment_id)
        return JsonResponse({"error": "No se pudo verificar el pago"}, status=503)
