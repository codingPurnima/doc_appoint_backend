
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base


class DoctorApprovalToken(Base):
    __tablename__ = "doctor_approval_tokens"

    id = Column(Integer, primary_key=True, index=True)

    doctor_profile_id = Column(
        Integer,
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
