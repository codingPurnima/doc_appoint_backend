from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.core.security import get_hashed_password, create_access_token, verify_password
from app.models.enums import RoleEnum
from app.core.config import settings


router= APIRouter(
    prefix="",
    tags=["Authentication"]
)

# PATIENT REGISTER ENDPOINT 
@router.post("/register", status_code=201)
def register(user: UserCreate, db: Session=Depends(get_db)):
    does_exist= db.query(User).filter(
        (User.name==user.username) | (User.phone==user.phone)
    ).first()

    if does_exist:
        raise HTTPException(status_code=400, detail='User exists already')
    
    new_user=User(
        name=user.username,
        phone=user.phone,
        hashed_password=get_hashed_password(user.password),
        role= RoleEnum.patient # hardcoded so no patient can register as a doctor
    )

    db.add(new_user) 
    db.commit() 
    db.refresh(new_user)

    return {"message": "User created"}

# DUMMY DATA
# {
#   "username": "Mishra",
#   "phone": "1478523698",
#   "password": "middss123"
# }


# DOCTOR REGISTER ENDPOINT
@router.post("/register/doctor")
def register_doctor(
    doctor: UserCreate,
    secret: str,
    db: Session= Depends(get_db)
):
    if secret != settings.DOCTOR_REGISTER_SECRET:
        raise HTTPException(status_code= 403, detail="Not allowed")
    
    user= User(
        name= doctor.username,
        phone= doctor.phone,
        hashed_password= get_hashed_password(doctor.password),
        role= RoleEnum.doctor
    )
    db.add(user)
    db.commit()
    return {"message": "Doctor registered successfully"}

# IN OUR DATABASE:
# {
#   "username": "Dr. Ajay",
#   "phone": "9632587410",
#   "password": "doct1number@Z"
# }



# LOGIN ENDPOINT 
@router.post("/login", response_model=Token) 
def login(
    form_data: OAuth2PasswordRequestForm= Depends(),
    db: Session=Depends(get_db)
):
    user=db.query(User).filter(User.name==form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token=create_access_token({"sub": user.name})

    return{
        "access_token": token,
        "token_type": "bearer"
    }

