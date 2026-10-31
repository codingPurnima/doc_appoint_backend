
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
from fastapi.responses import HTMLResponse

from app.models.doctor_approval_token import DoctorApprovalToken

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.doctor_profile import DoctorProfile
from app.models.enums import ApplicationStatusEnum, RoleEnum
from app.schemas.doctor_profile import (
    DoctorProfileCreate,
    DoctorProfileResponse,
    DoctorApplicationCreate
)
from app.services.email_service import send_doctor_application_email

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


@router.post("/apply", status_code=201)
async def submit_doctor_application(
    data: DoctorApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != RoleEnum.patient:
        raise HTTPException(
            status_code=403,
            detail="Only patient accounts can apply as doctors",
        )

    existing = db.query(DoctorProfile).filter(
        DoctorProfile.doctor_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="A doctor application already exists",
        )

    registration_exists = db.query(DoctorProfile).filter(
        DoctorProfile.registration_number == data.registration_number
    ).first()

    if registration_exists:
        raise HTTPException(
            status_code=409,
            detail="Registration number already exists",
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    profile = DoctorProfile(
        **data.model_dump(),
        doctor_id=current_user.id,
        is_approved=False,
        application_status=ApplicationStatusEnum.pending,
    )

    db.add(profile)
    db.flush()

    approval_token = DoctorApprovalToken(
        doctor_profile_id=profile.id,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=48),
        created_at=now,
    )

    db.add(approval_token)
    db.commit()
    db.refresh(profile)

    try:
        backend_url = os.getenv("BACKEND_PUBLIC_URL")

        if not backend_url:
            raise RuntimeError("BACKEND_PUBLIC_URL is not configured")

        review_url = (
            f"{backend_url.rstrip('/')}/doctors/review/{raw_token}"
        )

        await send_doctor_application_email(
            doctor_details=data.model_dump(),
            review_url=review_url,
        )

    except Exception as e:
        import traceback

        print("========== DOCTOR APPLICATION EMAIL ERROR ==========")
        traceback.print_exc()
        print("====================================================")

        raise HTTPException(
            status_code=503,
            detail="Application saved, but email notification failed.",
        )

    return {
        "message": "Application submitted. Awaiting verification.",
        "status": "pending",
    }



def get_valid_approval_token(token: str, db: Session):
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    approval_token = db.query(DoctorApprovalToken).filter(
        DoctorApprovalToken.token_hash == token_hash
    ).first()

    if not approval_token:
        raise HTTPException(status_code=404, detail="Invalid review link")

    if approval_token.used_at is not None:
        raise HTTPException(
            status_code=410,
            detail="This review link has already been used",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if approval_token.expires_at < now:
        raise HTTPException(
            status_code=410,
            detail="This review link has expired",
        )

    profile = db.query(DoctorProfile).filter(
        DoctorProfile.id == approval_token.doctor_profile_id
    ).first()

    if not profile or profile.application_status != ApplicationStatusEnum.pending:
        raise HTTPException(
            status_code=409,
            detail="Application is no longer pending",
        )

    return approval_token, profile


@router.get("/review/{token}", response_class=HTMLResponse)
def review_doctor_application(
    token: str,
    db: Session = Depends(get_db),
):
    approval_token, profile = get_valid_approval_token(token, db)

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>DocAppoint - Doctor Verification</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 60px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
            }}
            button {{
                padding: 12px 20px;
                border: 0;
                border-radius: 5px;
                cursor: pointer;
                margin: 10px 5px 0 0;
                color: white;
            }}
            .approve {{ background: #198754; }}
            .reject {{ background: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Doctor Application Review</h2>
            <p><strong>Name:</strong> {profile.full_name}</p>
            <p><strong>Specialization:</strong> {profile.specialization}</p>
            <p><strong>Qualification:</strong> {profile.qualification}</p>
            <p><strong>Registration Number:</strong>
                {profile.registration_number}</p>
            <p><strong>Clinic:</strong> {profile.clinic_name}</p>
            <p><strong>Experience:</strong>
                {profile.experience_years} years</p>
            <p>Please verify the doctor's credentials before deciding.</p>

            <form method="post" action="/doctors/review/{token}/approve">
                <button class="approve" type="submit">
                    Approve Application
                </button>
            </form>

            <form method="post" action="/doctors/review/{token}/reject">
                <button class="reject" type="submit">
                    Reject Application
                </button>
            </form>
        </div>
    </body>
    </html>
    """)


@router.post("/review/{token}/approve")
def approve_doctor_application(
    token: str,
    db: Session = Depends(get_db),
):
    approval_token, profile = get_valid_approval_token(token, db)

    user = db.query(User).filter(
        User.id == profile.doctor_id
    ).first()

    if not user or user.role != RoleEnum.patient:
        raise HTTPException(
            status_code=409,
            detail="Applicant account is not eligible for approval",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    profile.application_status = ApplicationStatusEnum.approved
    profile.is_approved = True
    user.role = RoleEnum.doctor
    approval_token.used_at = now

    db.commit()

    return HTMLResponse("""
        <h2>Application approved successfully.</h2>
        <p>The applicant can now access doctor features.</p>
    """)


@router.post("/review/{token}/reject")
def reject_doctor_application(
    token: str,
    db: Session = Depends(get_db),
):
    approval_token, profile = get_valid_approval_token(token, db)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    profile.application_status = ApplicationStatusEnum.rejected
    profile.is_approved = False
    approval_token.used_at = now

    db.commit()

    return HTMLResponse("""
        <h2>Application rejected.</h2>
        <p>The applicant's account remains a patient account.</p>
    """)
