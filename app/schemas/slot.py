from pydantic import BaseModel
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
