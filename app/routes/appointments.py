from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.slot import Slots
from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate
from app.core.security import get_current_user
from app.models.enums import StatusEnum, RoleEnum

router = APIRouter(prefix="/appointments", tags=["Appointments"])

@router.post("/book", status_code=status.HTTP_201_CREATED)
def book_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # current_user.role is stored as RoleEnum; compare against RoleEnum.patient
    if current_user.role != RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Only patients can book appointments")

    # Fetch slot
    slot = (
        db.query(Slots)
        .filter(Slots.id == data.slot_id)
        .with_for_update()
        .first()
    )

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    if slot.status != StatusEnum.available:
        raise HTTPException(status_code=400, detail="Slot not available")

    # Enforce one booking per day per patient
    existing_booking = (
        db.query(Appointment)
        .join(Slots)
        .filter(
            Appointment.patient_id == current_user.id,
            Appointment.status == StatusEnum.booked,
            Slots.date == slot.date
        )
        .first()
    )

    if existing_booking:
        raise HTTPException(
            status_code=400,
            detail="You already have a booking for this date"
        )

    # Create appointment
    appointment = Appointment(
        slot_id=slot.id,
        patient_id=current_user.id,
        status=StatusEnum.booked
    )

    slot.status = StatusEnum.booked

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "message": "Appointment booked successfully",
        "appointment_id": appointment.id
    }
