from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.slot import Slots
from app.models.user import User
from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate
from app.core.security import get_current_user
from app.models.enums import StatusEnum, RoleEnum

router = APIRouter(tags=["Appointments"])

@router.post("/book", status_code=status.HTTP_201_CREATED)
def book_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User= Depends(get_current_user)
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


@router.patch("/{appointment_id}/complete")
def complete_appointment(
    appointment_id: int,
    db: Session= Depends(get_db),
    current_user: User= Depends(get_current_user)
):
    if current_user.role != RoleEnum.doctor:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    appointment=(
        db.query(Appointment)
        .filter(Appointment.id== appointment_id)
        .first()
    )

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appointment.status= StatusEnum.completed
    db.commit()

    return {"message": "Appointment marked as completed"}


@router.get("/me")
def get_my_appointments(
    current_user: User = Depends(get_current_user),
    db: Session= Depends(get_db)
):
    if current_user.role!= RoleEnum.patient:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    results=(
        db.query(Appointment, Slots)
        .join(Slots, Appointment.slot_id== Slots.id)
        .filter(Appointment.patient_id== current_user.id)
        .order_by(Slots.date.desc())
        .all()
    )

    return [
        {
            "appointment_id": appointment.id,
            "status": appointment.status,
            "date": slot.date,
            "start_time": slot.start_time,
            "end_time": slot.end_time
        }
        for appointment, slot in results
    ]

@router.get("/doctor")
def get_doctor_appointments(
    db: Session= Depends(get_db),
    current_user: User= Depends(get_current_user)
):
    if current_user.role!= RoleEnum.doctor:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    appointments=(
        db.query(Appointment, Slots, User)
        .join(Slots, Appointment.slot_id == Slots.id)
        .join(User, Appointment.patient_id== User.id)
        .filter(Slots.doctor_id== current_user.id)
        .order_by(Slots.date.desc(), Slots.start_time.desc())
        .all()
    )
    response = []

    for appointment, slot, patient in appointments:
        print("PATIENT:", patient.id, patient.name)
        response.append({
            "appointment_id": appointment.id,
            "date": slot.date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "status": appointment.status,
            "patient_name": patient.name
        })

    return response

@router.put("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    current_user: User= Depends(get_current_user),
    db: Session= Depends(get_db)
):
    appointment= db.query(Appointment).filter(
        Appointment.id== appointment_id,
        Appointment.patient_id== current_user.id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.status != StatusEnum.booked:
        raise HTTPException(status_code=400, detail="Cannot cancel")
    
    slot= db.query(Slots).filter(Slots.id== appointment.slot_id).first()
    appointment.status = StatusEnum.cancelled
    slot.status = StatusEnum.available

    db.commit()

    return {"message": "Appointment cancelled successfully"}
