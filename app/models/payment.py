from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum as SQLAEnum,
    func,
)
from app.models.enums import PaymentStatusEnum
from app.database import Base 




class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=False,
        index=True,
    )

    amount = Column(Integer, nullable=False)  # Store paise: ₹10 = 1000
    currency = Column(String(3), nullable=False, default="INR")

    razorpay_order_id = Column(String(100), unique=True, nullable=False)
    razorpay_payment_id = Column(String(100), unique=True, nullable=True)

    status = Column(
        SQLAEnum(
            PaymentStatusEnum,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=PaymentStatusEnum.created,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )