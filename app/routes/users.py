from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.slot import Slots
from app.models.appointment import Appointment
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