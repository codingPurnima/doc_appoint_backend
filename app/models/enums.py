from enum import Enum

class RoleEnum(str, Enum):
    doctor= "doctor"
    patient= "patient"


class StatusEnum(str, Enum):
    available= "available"
    booked= "booked"
    completed= "completed"
    cancelled= "cancelled"
    frozen= "frozen"
    pending_payment= "pending_payment"

class PaymentStatusEnum(str, Enum):
    created = "created"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"

class ApplicationStatusEnum(str, Enum):
    pending= "pending"
    approved= "approved"
    rejected= "rejected"