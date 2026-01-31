from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Enum as SQLAEnum
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import StatusEnum

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Use SQLAlchemy Enum column type mapping to our StatusEnum
    status = Column(SQLAEnum(StatusEnum), default=StatusEnum.booked)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
