
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class DoctorProfileCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    specialization: str = Field(min_length=1, max_length=200)
    qualification: str = Field(min_length=1, max_length=200)
    registration_number: str = Field(min_length=1, max_length=100)
    clinic_name: str = Field(min_length=1, max_length=150)
    clinic_address: str = Field(min_length=1, max_length=500)
    consultation_fee: int = Field(ge=0)
    experience_years: int = Field(ge=0)
    bio: Optional[str] = Field(default=None, max_length=1000)
    profile_image_url: Optional[str] = Field(
        default=None, max_length=500
    )


class DoctorProfileResponse(DoctorProfileCreate):
    id: int
    doctor_id: int
    is_approved: bool

    model_config = ConfigDict(from_attributes=True)

class DoctorApplicationCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    specialization: str = Field(min_length=1, max_length=200)
    qualification: str = Field(min_length=1, max_length=200)
    registration_number: str = Field(min_length=1, max_length=100)
    clinic_name: str = Field(min_length=1, max_length=150)
    clinic_address: str = Field(min_length=1, max_length=500)
    consultation_fee: int = Field(ge=0)
    experience_years: int = Field(ge=0)
    bio: Optional[str] = Field(default=None, max_length=1000)
    profile_image_url: Optional[str] = Field(
        default=None, max_length=500
    )