import httpx
import base64
import time
from datetime import datetime
from app.config import settings
from models.order import Order


class MpesaProvider:
    SANDBOX_URL = "https://sandbox.safaricom.co.ke"
    PROD_URL = "https://api.safaricom.co.ke"

    def _base_url(self) -> str:
        return self.SANDBOX_URL

    async def _get_access_token(self) -> str:
        credentials = base64.b64encode(
            f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()
        ).decode()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._base_url()}/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {credentials}"},
            )
            return response.json()["access_token"]

    def _get_password(self, timestamp: str) -> str:
        raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    async def initiate(self, order: Order, return_url: str | None = None) -> dict:
        token = await self._get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = self._get_password(timestamp)

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(float(order.total)),
            "PartyA": order.customer_phone or "",
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": order.customer_phone or "",
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": order.id[:12],
            "TransactionDesc": f"Order {order.id[:8]}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url()}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            data = response.json()

        return {
            "provider": "mpesa",
            "checkout_request_id": data.get("CheckoutRequestID"),
            "merchant_request_id": data.get("MerchantRequestID"),
            "raw": data,
        }

    async def verify(self, checkout_request_id: str) -> dict:
        return {"status": "pending", "checkout_request_id": checkout_request_id}
