from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_

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
    patient=(
        db.query(User)
        .filter(User.id== current_user.id)
        .with_for_update()
        .first()
    )
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
                Slots.date == slot.date,
                or_(
                    Appointment.status == StatusEnum.booked,
                    and_(
                        Appointment.status == StatusEnum.pending_payment,
                        Appointment.payment_status == "created",
                        Appointment.reservation_expires_at > now,
                    ),
                ),
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail=(
                    "You already have a booked appointment or pending payment "
                    "for this date. Complete or resolve it before booking another."
                ),
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
    if current_user.role != RoleEnum.patient:
        raise HTTPException(
            status_code=403,
            detail="Only patients can verify appointment payments",
        )

    try:
        # 1. Lock the patient first so concurrent bookings and verifications
        #    for this patient follow the same locking order.
        patient = (
            db.query(User)
            .filter(User.id == current_user.id)
            .with_for_update()
            .first()
        )

        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # 2. Lock and retrieve the payment.
        payment = (
            db.query(Payment)
            .filter(
                Payment.razorpay_order_id == data.razorpay_order_id
            )
            .with_for_update()
            .first()
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="Payment order not found",
            )

        # 3. Lock and retrieve the appointment belonging to this patient.
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
            raise HTTPException(
                status_code=404,
                detail="Appointment not found",
            )

        # 4. Handle repeated verification safely.
        if (
            payment.status == PaymentStatusEnum.paid
            and appointment.payment_status == "paid"
        ):
            if appointment.status == StatusEnum.booked:
                db.commit()
                return {
                    "message": "Payment already verified",
                    "appointment_id": appointment.id,
                    "status": "booked",
                    "payment_status": "paid",
                }

            # The payment was captured, but this appointment was not confirmed.
            # Do not report it as booked; its refund/reconciliation needs attention.
            db.commit()
            return {
                "message": (
                    "Payment was already captured, but the appointment "
                    "is not confirmed. A refund needs to be resolved."
                ),
                "appointment_id": appointment.id,
                "status": "cancelled",
                "payment_status": "paid",
                "refund_required": True,
            }

        # 5. Only an active pending reservation can be verified.
        if (
            appointment.status != StatusEnum.pending_payment
            or appointment.payment_status != "created"
            or payment.status != PaymentStatusEnum.created
        ):
            raise HTTPException(
                status_code=400,
                detail="This booking is no longer awaiting payment",
            )

        # 6. Verify the signature first.
        client = get_razorpay_client()

        try:
            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": data.razorpay_order_id,
                    "razorpay_payment_id": data.razorpay_payment_id,
                    "razorpay_signature": data.razorpay_signature,
                }
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature",
            )

        # 7. Confirm with Razorpay whether the money was actually captured.
        try:
            razorpay_payment = client.payment.fetch(
                data.razorpay_payment_id
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="Could not confirm payment status with Razorpay",
            ) from exc

        if razorpay_payment.get("order_id") != payment.razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail="Payment does not match this order",
            )

        if razorpay_payment.get("status") != "captured":
            raise HTTPException(
                status_code=400,
                detail="Payment is not captured yet. Please try again shortly.",
            )

        # 8. The payment is captured. Record that fact before deciding
        #    whether the appointment can still be confirmed.
        payment.razorpay_payment_id = data.razorpay_payment_id
        payment.status = PaymentStatusEnum.paid

        # Lock the appointment's slot.
        current_slot = (
            db.query(Slots)
            .filter(Slots.id == appointment.slot_id)
            .with_for_update()
            .first()
        )

        if not current_slot:
            appointment.status = StatusEnum.cancelled
            appointment.payment_status = "paid"
            appointment.reservation_expires_at = None
            db.commit()

            return {
                "message": (
                    "Payment was captured, but the appointment slot "
                    "could not be found. A refund needs to be resolved."
                ),
                "appointment_id": appointment.id,
                "status": "cancelled",
                "payment_status": "paid",
                "refund_required": True,
            }

        # 9. Check whether the reservation expired.
        now = datetime.now(timezone.utc)
        reservation_expired = (
            appointment.reservation_expires_at is not None
            and appointment.reservation_expires_at <= now
        )

        # 10. Recheck the daily booking limit immediately before confirmation.
        #     Another booked appointment on the same date means this payment
        #     cannot create a second confirmed appointment.
        conflicting_appointment = (
            db.query(Appointment)
            .join(Slots, Appointment.slot_id == Slots.id)
            .filter(
                Appointment.patient_id == current_user.id,
                Appointment.id != appointment.id,
                Appointment.status == StatusEnum.booked,
                Slots.date == current_slot.date,
            )
            .first()
        )

        if reservation_expired or conflicting_appointment:
            # The payment has been captured, so do not mark it as failed.
            # Preserve the captured-payment record and flag the refund.
            appointment.status = StatusEnum.cancelled
            appointment.payment_status = "paid"
            appointment.reservation_expires_at = None

            # Release the slot only if no other active appointment
            # still uses it.
            other_active_appointment = (
                db.query(Appointment)
                .filter(
                    Appointment.slot_id == current_slot.id,
                    Appointment.id != appointment.id,
                    Appointment.status.in_(
                        [
                            StatusEnum.booked,
                            StatusEnum.pending_payment,
                        ]
                    ),
                )
                .first()
            )

            if not other_active_appointment:
                current_slot.status = StatusEnum.available

            db.commit()

            if reservation_expired:
                message = (
                    "Payment was captured after the reservation expired. "
                    "A refund needs to be resolved."
                )
            else:
                message = (
                    "Payment was captured, but you already have an "
                    "appointment booked for this date. "
                    "A refund needs to be resolved."
                )

            return {
                "message": message,
                "appointment_id": appointment.id,
                "status": "cancelled",
                "payment_status": "paid",
                "refund_required": True,
            }

        # 11. All checks passed. Confirm the appointment.
        appointment.payment_status = "paid"
        appointment.status = StatusEnum.booked
        appointment.reservation_expires_at = None
        current_slot.status = StatusEnum.booked

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
        raise HTTPException(
            status_code=502,
            detail="Could not verify payment",
        ) from exc

@router.get("/pending")
def get_pending_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Patients only")

    # Release expired reservations before retrieving pending payments.
    expire_pending_reservations(db)

    now = datetime.now(timezone.utc)

    results = (
        db.query(Appointment, Payment, Slots)
        .join(Payment, Payment.appointment_id == Appointment.id)
        .join(Slots, Slots.id == Appointment.slot_id)
        .filter(
            Appointment.patient_id == current_user.id,
            Appointment.status == StatusEnum.pending_payment,
            Appointment.payment_status == "created",
            Appointment.reservation_expires_at > now,
            Payment.status == PaymentStatusEnum.created,
        )
        .order_by(Appointment.reservation_expires_at.asc())
        .all()
    )

    key_id = os.getenv("RAZORPAY_KEY_ID")
    if not key_id:
        raise HTTPException(
            status_code=500,
            detail="Payment configuration is missing",
        )

    pending = []

    for appointment, payment, slot in results:
        pending.append({
            "appointment_id": appointment.id,
            "slot_id": slot.id,
            "date": slot.date.isoformat(),
            "start_time": slot.start_time.isoformat(),
            "end_time": slot.end_time.isoformat(),
            "order_id": payment.razorpay_order_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "key_id": key_id,
            "reservation_expires_at":
                appointment.reservation_expires_at.isoformat(),
        })

    return {"pending_payments": pending}