import os
import razorpay

from fastapi import HTTPException


def get_razorpay_client():
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise HTTPException(
            status_code=500,
            detail="Payment gateway is not configured",
        )

    return razorpay.Client(
        auth=(key_id, key_secret)
    )