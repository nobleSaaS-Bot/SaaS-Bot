from fastapi import APIRouter, Request, HTTPException
from core.queue import enqueue_payment_job

router = APIRouter()


@router.post("/")
async def mpesa_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    stk_callback = payload.get("Body", {}).get("stkCallback", {})
    result_code = stk_callback.get("ResultCode")
    checkout_request_id = stk_callback.get("CheckoutRequestID")

    if not checkout_request_id:
        raise HTTPException(status_code=400, detail="Missing CheckoutRequestID")

    if result_code == 0:
        enqueue_payment_job(checkout_request_id, "mpesa", {"status": "completed", "raw": stk_callback})
    else:
        enqueue_payment_job(checkout_request_id, "mpesa", {"status": "failed", "raw": stk_callback})

    return {"ResultCode": 0, "ResultDesc": "Accepted"}
