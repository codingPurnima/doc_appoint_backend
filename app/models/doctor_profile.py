from sqlalchemy import Boolean, CheckConstraint, Column, Integer, String, ForeignKey, DateTime, Enum as SQLAEnum
from sqlalchemy.orm import relationship
from app.database import Base

from app.models.user import User
from app.models.enums import ApplicationStatusEnum

class DoctorProfile(Base):
    __tablename__='doctor_profiles'
    id= Column(Integer, primary_key=True, index=True)
    doctor_id= Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable= False)
    full_name= Column(String(100), nullable=False)
    specialization= Column(String(200), nullable= False)
    qualification= Column(String, nullable=False)
    registration_number= Column(String(100), nullable= False, unique=True)
    clinic_name= Column(String(100), nullable=False, default='SELF')
    clinic_address= Column(String(500), nullable=False, default=' ')
    consultation_fee= Column(Integer, nullable=False, default= 0)
    experience_years= Column(Integer, nullable=False, default=0)
    bio= Column(String(1000), nullable=True)
    profile_image_url= Column(String(500), nullable=True)
    is_approved= Column(Boolean, nullable=False, default= False)

    application_status = Column(
        SQLAEnum(ApplicationStatusEnum, native_enum=False),
        nullable=False,
        default=ApplicationStatusEnum.pending,
    )

    doctor= relationship("User", back_populates="doctor_profile")

    __table_args__ = (
        CheckConstraint(
            "consultation_fee >= 0",
            name="check_doctor_consultation_fee_nonnegative",
        ),
        CheckConstraint(
            "experience_years >= 0",
            name="check_doctor_experience_nonnegative",
        ),

     )