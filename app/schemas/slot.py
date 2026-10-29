from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import time, date

class BreakInterval(BaseModel):
    start: time
    end: time

class SlotGenerateRequest(BaseModel):
    date: date
    day_start: time
    day_end: time
    slot_duration_minutes: int
    breaks: Optional[List[BreakInterval]] = []

class SlotGenerateRangeRequest(BaseModel):
    start_date: date
    duration_days: int = Field(ge=1, le=14)
    weekdays_only: bool = False
    day_start: time
    day_end: time
    slot_duration_minutes: int = Field(gt=0)
    breaks: List[BreakInterval] = Field(default_factory=list)