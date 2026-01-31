from pydantic import BaseModel

class AppointmentCreate(BaseModel):
    slot_id: int
