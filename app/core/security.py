from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext 
from datetime import datetime, timedelta 
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer 
from app.database import get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.config import settings


SECRET_KEY= settings.SECRET_KEY

pwd_context=CryptContext(
    schemes=['bcrypt'], 
    deprecated='auto' 
)


oauth2_scheme= OAuth2PasswordBearer(tokenUrl="/login")


def get_hashed_password(password: str)->str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str)-> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):  
    to_encode=data.copy()  
    expire= datetime.utcnow()+timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) 
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict):
    to_encode= data.copy()
    expire= datetime.utcnow()+timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode, SECRET_KEY, algorithm=settings.ALGORITHM
    )

def decode_refresh_token(token: str):
    try:
        payload= jwt.decode(token, SECRET_KEY, algorithms=[settings.ALGORITHM])
        name= payload.get("sub")

        if name is None:
            return None
        
        return name
    except JWTError:
        return None


def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
    ):
    try:
        payload=jwt.decode(token, SECRET_KEY, algorithms=[settings.ALGORITHM]) 
        username=payload.get("sub") 

        if username is None: 
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.name == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )