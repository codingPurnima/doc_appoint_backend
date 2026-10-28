from fastapi import FastAPI
from app.routes import auth, payments, slots, appointments, users, doctor_profiles
from app.database import Base, engine
from app.models.payment import Payment
from app.models.doctor_profile import DoctorProfile
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5000",
        "http://localhost:61226",
        "http://127.0.0.1:61226",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(slots.router, prefix="/slots")
app.include_router(appointments.router, prefix="/appointments")
app.include_router(users.router, prefix="/users")
app.include_router(payments.router)
app.include_router(doctor_profiles.router)

Base.metadata.create_all(bind=engine)

# NOT MANDATORY
# @app.get("/")
# def root():
#     return {"message": "hello"}
