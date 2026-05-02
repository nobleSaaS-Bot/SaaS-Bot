import httpx
import hashlib
import time
from app.config import settings
from models.order import Order


class TelebirrProvider:
    BASE_URL = "https://api.ethiomobilemoney.et:2443/ammapi/payment/service-openup"

    def _build_sign(self, params: dict) -> str:
        sorted_items = sorted(params.items())
        query = "&".join(f"{k}={v}" for k, v in sorted_items)
        query += f"&key={settings.TELEBIRR_APP_KEY}"
        return hashlib.sha256(query.encode()).hexdigest().upper()

    async def initiate(self, order: Order, return_url: str | None = None) -> dict:
        timestamp = str(int(time.time()))
        nonce = hashlib.md5(f"{order.id}{timestamp}".encode()).hexdigest()

        params = {
            "appId": settings.TELEBIRR_APP_ID,
            "appKey": settings.TELEBIRR_APP_KEY,
            "notifyUrl": settings.TELEBIRR_NOTIFY_URL,
            "outTradeNo": order.id,
            "shortCode": settings.TELEBIRR_SHORT_CODE,
            "subject": f"Order {order.id[:8]}",
            "timeoutExpress": "30",
            "timestamp": timestamp,
            "totalAmount": str(float(order.total)),
            "nonce": nonce,
            "receiveName": "Merchant",
        }
        params["sign"] = self._build_sign(params)

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.BASE_URL}/toTradeWebpay", json=params, timeout=30)
            data = response.json()

        return {"provider": "telebirr", "raw": data, "out_trade_no": order.id}

    async def verify(self, out_trade_no: str) -> dict:
        return {"status": "pending", "out_trade_no": out_trade_no}
