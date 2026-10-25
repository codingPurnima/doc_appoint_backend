
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.doctor_profile import DoctorProfile
from app.models.enums import RoleEnum
from app.schemas.doctor_profile import (
    DoctorProfileCreate,
    DoctorProfileResponse,
)

router = APIRouter(prefix="/doctors", tags=["Doctor Profiles"])


@router.get(
    "/{doctor_id}/profile",
    response_model=DoctorProfileResponse,
)
def get_doctor_profile(
    doctor_id: int,
    db: Session = Depends(get_db),
):
    profile = db.query(DoctorProfile).filter(
        DoctorProfile.doctor_id == doctor_id,
        DoctorProfile.is_approved.is_(True),
    ).first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found",
        )

    return profile


@router.post(
    "/profile",
    response_model=DoctorProfileResponse,
    status_code=201,
)
def create_doctor_profile(
    data: DoctorProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != RoleEnum.doctor:
        raise HTTPException(
            status_code=403,
            detail="Only doctors can create profiles",
        )

    existing = db.query(DoctorProfile).filter(
        DoctorProfile.doctor_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Doctor profile already exists",
        )

    registration_exists = db.query(DoctorProfile).filter(
        DoctorProfile.registration_number == data.registration_number
    ).first()

    if registration_exists:
        raise HTTPException(
            status_code=409,
            detail="Registration number already exists",
        )

    profile = DoctorProfile(
        **data.model_dump(),
        doctor_id=current_user.id,
        is_approved=False,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile
