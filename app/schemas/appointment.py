from pydantic import BaseModel
from datetime import date, time

class AppointmentCreate(BaseModel):
    slot_id: int

class DoctorAppointmentResponse(BaseModel):
    appointment_id: int
    date: date
    start_time: time
    end_time: time
    status: str
    patient_name: str