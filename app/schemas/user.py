from pydantic import BaseModel
from app.models.enums import RoleEnum

class UserCreate(BaseModel):
    username: str
    phone: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

class UserLogin(BaseModel):
    phone: str
    password: str
    
class Token(BaseModel):
    access_token: str
    token_type: str