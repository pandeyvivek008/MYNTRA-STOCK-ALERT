"""Outbound WhatsApp alerts via the Meta WhatsApp Cloud API.

No message is sent until all WhatsApp variables are configured. A template is
used because inventory alerts are business-initiated notifications.
"""
import logging
import httpx
from .settings import settings

logger = logging.getLogger(__name__)

async def send_whatsapp_stock_alert(alert: dict) -> bool:
    required = [settings.whatsapp_access_token, settings.whatsapp_phone_number_id, settings.whatsapp_alert_to]
    if not all(required):
        return False
    url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{settings.whatsapp_phone_number_id}/messages"
    params = [alert["product"]["name"], alert["product"]["sku"], alert["variant"]["size"], alert["variant"].get("color", "Default"), str(alert["variant"]["quantity"]), alert["severity"].upper()]
    payload = {
        "messaging_product": "whatsapp", "to": settings.whatsapp_alert_to,
        "type": "template", "template": {"name": settings.whatsapp_template_name, "language": {"code": settings.whatsapp_template_language},
        "components": [{"type": "body", "parameters": [{"type": "text", "text": value} for value in params]}]},
    }
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"}, json=payload)
            response.raise_for_status()
        return True
    except httpx.HTTPError as error:
        logger.warning("WhatsApp stock alert delivery failed: %s", error)
        return False
