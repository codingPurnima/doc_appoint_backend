from datetime import date, datetime
from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.payment import Payment
from app.models.slot import Slots
from app.models.appointment import Appointment
from app.models.user import User
from app.schemas.appointment import AppointmentCreate
from app.core.security import get_current_user
from app.models.enums import StatusEnum, RoleEnum

router= APIRouter(tags= ["Users"])

@router.get("/me")
def get_current_user_details(
    current_user= Depends(get_current_user)
):
    return{
        "id": current_user.id,
        "name": current_user.name,
        "phone": current_user.phone,
        "role": current_user.role
    }



@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # -------------------------------------------------
        # PATIENT ACCOUNT DELETION
        # -------------------------------------------------
        if current_user.role == RoleEnum.patient:

            appointments = (
                db.query(Appointment, Slots)
                .join(Slots, Appointment.slot_id == Slots.id)
                .filter(Appointment.patient_id == current_user.id)
                .all()
            )

            today = date.today()
            now = datetime.now().time()

            # Release future booked slots before removing appointments.
            for appointment, slot in appointments:
                if appointment.status == StatusEnum.booked:
                    if (
                        slot.date > today
                        or (
                            slot.date == today
                            and slot.start_time > now
                        )
                    ):
                        slot.status = StatusEnum.available

            # Get appointment IDs belonging to this patient.
            appointment_ids = [
                appointment.id
                for appointment, slot in appointments
            ]

            if appointment_ids:

                # 1. Delete payments linked to these appointments.
                db.query(Payment).filter(
                    Payment.appointment_id.in_(appointment_ids)
                ).delete(synchronize_session=False)

                # 2. Delete patient's appointments.
                db.query(Appointment).filter(
                    Appointment.patient_id == current_user.id
                ).delete(synchronize_session=False)

        # -------------------------------------------------
        # DOCTOR ACCOUNT DELETION
        # -------------------------------------------------
        elif current_user.role == RoleEnum.doctor:

            # Find all slots owned by this doctor.
            slot_ids = [
                row[0]
                for row in db.query(Slots.id)
                .filter(Slots.doctor_id == current_user.id)
                .all()
            ]

            if slot_ids:

                # Get appointment IDs linked to doctor's slots.
                appointment_ids = [
                    row[0]
                    for row in db.query(Appointment.id)
                    .filter(Appointment.slot_id.in_(slot_ids))
                    .all()
                ]

                if appointment_ids:

                    # 1. Delete payments linked to these appointments.
                    db.query(Payment).filter(
                        Payment.appointment_id.in_(appointment_ids)
                    ).delete(synchronize_session=False)

                    # 2. Delete appointments linked to these slots.
                    db.query(Appointment).filter(
                        Appointment.slot_id.in_(slot_ids)
                    ).delete(synchronize_session=False)

                # 3. Delete the doctor's slots.
                db.query(Slots).filter(
                    Slots.doctor_id == current_user.id
                ).delete(synchronize_session=False)

        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account deletion not allowed",
            )

        # -------------------------------------------------
        # DELETE USER ACCOUNT
        # -------------------------------------------------

        # Delete the user.
        # The doctor_profile relationship has delete-orphan cascade.
        db.delete(current_user)

        db.commit()

        return {
            "message": "Account deleted successfully"
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account cannot be deleted because related records still exist",
        )

    except Exception:
        db.rollback()
        raise
