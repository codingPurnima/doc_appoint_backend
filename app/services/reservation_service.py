
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.appointment import Appointment, StatusEnum
from app.models.slot import Slots
from app.models.payment import Payment, PaymentStatus


def expire_pending_reservations(db: Session) -> int:
    now = datetime.now(timezone.utc)

    expired = (
        db.query(Appointment)
        .filter(
            Appointment.status == StatusEnum.pending_payment,
            Appointment.payment_status == "created",
            Appointment.reservation_expires_at <= now,
        )
        .with_for_update()
        .all()
    )

    expired_count = 0

    try:
        for appointment in expired:
            slot = (
                db.query(Slots)
                .filter(Slots.id == appointment.slot_id)
                .with_for_update()
                .first()
            )

            appointment.status = StatusEnum.cancelled
            appointment.payment_status = "failed"
            appointment.reservation_expires_at = None

            payment = (
                db.query(Payment)
                .filter(Payment.appointment_id == appointment.id)
                .first()
            )

            if payment and payment.status == PaymentStatus.created:
                payment.status = PaymentStatus.failed

            if slot:
                # Keep the slot unavailable if another valid
                # appointment already occupies it.
                other_appointments = (
                    db.query(Appointment)
                    .filter(
                        Appointment.slot_id == slot.id,
                        Appointment.id != appointment.id,
                    )
                    .all()
                )

                has_active_booking = any(
                    (
                        a.status == StatusEnum.booked
                        and (
                            a.payment_status == "paid"
                            or a.reservation_expires_at is None
                        )
                    )
                    or (
                        a.status == StatusEnum.pending_payment
                        and a.payment_status == "created"
                        and a.reservation_expires_at is not None
                        and a.reservation_expires_at > now
                    )
                    for a in other_appointments
                )

                if not has_active_booking:
                    slot.status = StatusEnum.available

            expired_count += 1

        db.commit()
        return expired_count

    except Exception:
        db.rollback()
        raise
