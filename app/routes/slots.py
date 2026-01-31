# api to generate slots

from fastapi import APIRouter, Depends, HTTPException, status, Query
from enum import Enum
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date

from app.database import get_db
from app.models.slot import Slots
from app.schemas.slot import SlotGenerateRequest
from app.core.security import get_current_user  
from app.models.enums import StatusEnum, RoleEnum

# Helper Functions
def time_to_minutes(t):
    return t.hour * 60 + t.minute

def minutes_to_time(m):
    return (datetime.min + timedelta(minutes=m)).time()


router = APIRouter(tags=["Slots"])

@router.post("/generate")
def generate_slots(
    request: SlotGenerateRequest,
    db: Session= Depends(get_db),
    current_user= Depends(get_current_user)
):
    # current_user.role is an instance of RoleEnum; compare against RoleEnum.doctor
    if current_user.role != RoleEnum.doctor:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    slot_exists = db.query(Slots).filter(
        Slots.doctor_id == current_user.id,
        Slots.date == request.date
    ).first()

    if slot_exists:
        raise HTTPException(status_code=400, detail="Slots for this date exist")
    
    start_minutes = time_to_minutes(request.day_start)
    end_minutes = time_to_minutes(request.day_end)
    duration = request.slot_duration_minutes

    breaks = [
        (time_to_minutes(b.start), time_to_minutes(b.end))
        for b in request.breaks
    ]

    slots_created = 0
    current = start_minutes

    while current + duration <= end_minutes:
        # Check if slot overlaps a break
        in_break = False
        for b_start, b_end in breaks: # these variables come from unpacking each tuple inside the breaks list from above
            if current < b_end and current + duration > b_start:
                current = b_end
                in_break = True
                break

        if in_break:
            continue

        slot = Slots(
            doctor_id=current_user.id,
            date=request.date,
            start_time=minutes_to_time(current),
            end_time=minutes_to_time(current + duration),
            status=StatusEnum.available
        )

        db.add(slot)
        slots_created += 1
        current += duration

    db.commit()

    return {
        "message": "Slots generated successfully",
        "slots_created": slots_created
    }


