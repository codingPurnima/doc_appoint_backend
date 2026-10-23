from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.appointment import Appointment, StatusEnum
from app.models.slot import Slots
from app.models.payment import Payment, PaymentStatusEnum
from app.models.user import User, RoleEnum
from app.core.security import get_current_user
from app.schemas.payment import VerifyPaymentRequest
from app.services.payment_service import get_razorpay_client

import os

from app.services.reservation_service import expire_pending_reservations


router = APIRouter(prefix="/payments", tags=["Payments"])

CONSULTATION_FEE_PAISE = 1000
RESERVATION_MINUTES = 10


@router.post("/create-booking")
def create_booking_payment(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(403, "Only patients can book appointments")
    expire_pending_reservations(db)
    try:
        slot = (
            db.query(Slots)
            .filter(Slots.id == slot_id)
            .with_for_update()
            .first()
        )

        if not slot:
            raise HTTPException(404, "Slot not found")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=RESERVATION_MINUTES)

        # Release expired, unpaid reservations for this slot.
        expired = (
            db.query(Appointment)
            .filter(
                Appointment.slot_id == slot.id,
                Appointment.payment_status == "created",
                Appointment.reservation_expires_at <= now,
            )
            .first()
        )

        if expired:
            expired.payment_status = "failed"
            expired.status = StatusEnum.cancelled
            slot.status = StatusEnum.available

        if slot.status != StatusEnum.available:
            db.rollback()
            raise HTTPException(400, "Slot is not available")

        existing = (
            db.query(Appointment)
            .join(Slots, Appointment.slot_id == Slots.id)
            .filter(
                Appointment.patient_id == current_user.id,
                Appointment.status == StatusEnum.booked,
                Slots.date == slot.date,
            )
            .first()
        )

        if existing:
            db.rollback()
            raise HTTPException(
                400, "You already have a booking for this date"
            )

        appointment = Appointment(
            slot_id=slot.id,
            patient_id=current_user.id,
            status=StatusEnum.pending_payment,
            payment_status="created",
            reservation_expires_at=expires_at,
        )
        db.add(appointment)
        db.flush()

        client = get_razorpay_client()
        order = client.order.create({
            "amount": CONSULTATION_FEE_PAISE,
            "currency": "INR",
            "receipt": f"appt_{appointment.id}",
        })

        payment = Payment(
            appointment_id=appointment.id,
            amount=CONSULTATION_FEE_PAISE,
            currency="INR",
            razorpay_order_id=order["id"],
            status=PaymentStatusEnum.created,
        )
        db.add(payment)

        slot.status = StatusEnum.booked
        db.commit()

        return {
            "appointment_id": appointment.id,
            "order_id": order["id"],
            "amount": CONSULTATION_FEE_PAISE,
            "currency": "INR",
            "reservation_expires_at": expires_at.isoformat(),
            "key_id": os.getenv("RAZORPAY_KEY_ID"),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            502, "Could not create booking payment"
        ) from exc



@router.post("/verify")
def verify_payment(
    data: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = get_razorpay_client()

    payment = (
        db.query(Payment)
        .filter(Payment.razorpay_order_id == data.razorpay_order_id)
        .with_for_update()
        .first()
    )

    if not payment:
        raise HTTPException(404, "Payment order not found")

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == payment.appointment_id,
            Appointment.patient_id == current_user.id,
        )
        .with_for_update()
        .first()
    )

    if not appointment:
        raise HTTPException(404, "Appointment not found")

    if (
        payment.status == PaymentStatusEnum.paid
        and appointment.payment_status == "paid"
    ):
        return {
            "message": "Payment already verified",
            "appointment_id": appointment.id,
            "status": "booked",
        }

    if (
        appointment.status != StatusEnum.pending_payment
        or appointment.payment_status != "created"
    ):
        raise HTTPException(400, "This booking is no longer awaiting payment")

    if (
        appointment.reservation_expires_at
        and appointment.reservation_expires_at <= datetime.now(timezone.utc)
    ):
        appointment.status = StatusEnum.cancelled
        appointment.payment_status = "failed"
        payment.status = PaymentStatusEnum.failed
        db.commit()
        raise HTTPException(400, "Reservation expired. Please book another slot.")

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature,
        })
    except Exception:
        raise HTTPException(400, "Invalid payment signature")

    try:
        razorpay_payment = client.payment.fetch(data.razorpay_payment_id)

        if razorpay_payment.get("order_id") != payment.razorpay_order_id:
            raise HTTPException(400, "Payment does not match this order")

        if razorpay_payment.get("status") != "captured":
            raise HTTPException(
                400,
                "Payment is not captured yet. Please try again shortly.",
            )

        payment.razorpay_payment_id = data.razorpay_payment_id
        payment.status = PaymentStatusEnum.paid
        appointment.payment_status = "paid"
        appointment.status = StatusEnum.booked
        appointment.reservation_expires_at = None

        db.commit()

        return {
            "message": "Payment verified successfully",
            "appointment_id": appointment.id,
            "status": "booked",
            "payment_status": "paid",
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, "Could not verify payment") from exc