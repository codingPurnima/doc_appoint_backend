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