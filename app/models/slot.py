from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, Date, Time, Enum as SQLAEnum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
from app.models.enums import StatusEnum
from app.models.user import User

class Slots(Base):
    __tablename__ = 'slots'

    id= Column(Integer, primary_key=True, nullable=False, index= True)
    doctor_id= Column(Integer, ForeignKey("users.id"), nullable= False)

    date= Column(Date)
    start_time= Column(Time)
    end_time= Column(Time)

    status= Column(SQLAEnum(StatusEnum), default=StatusEnum.available, nullable=False)
# date + start_time + doctor_id identifies a slot uniquely
