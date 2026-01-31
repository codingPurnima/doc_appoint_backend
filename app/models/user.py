from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Enum as SQLAEnum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
from app.models.enums import RoleEnum

class User(Base):
    __tablename__= 'users'
    id=Column(Integer, primary_key=True, index=True)
    name=Column(String(50), unique= True, index= True, nullable= False)
    phone = Column(String(10), unique= True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLAEnum(RoleEnum), default=RoleEnum.patient, nullable=False)