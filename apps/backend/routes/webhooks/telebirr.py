from fastapi import APIRouter, Request, HTTPException
from core.queue import enqueue_payment_job

router = APIRouter()


@router.post("/")
async def telebirr_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    trade_status = payload.get("trade_status")
    out_trade_no = payload.get("out_trade_no")

    if not out_trade_no:
        raise HTTPException(status_code=400, detail="Missing out_trade_no")

    if trade_status == "SUCCESS":
        enqueue_payment_job(out_trade_no, "telebirr", {"status": "completed", "raw": payload})
    elif trade_status in ("FAILED", "CLOSED"):
        enqueue_payment_job(out_trade_no, "telebirr", {"status": "failed", "raw": payload})

    return {"result_code": "0", "result_msg": "OK"}
