from fastapi import FastAPI
from app.routes import auth, payments, slots, appointments, users
from app.database import Base, engine
from app.models.payment import Payment

app = FastAPI()

app.include_router(auth.router)
app.include_router(slots.router, prefix="/slots")
app.include_router(appointments.router, prefix="/appointments")
app.include_router(users.router, prefix="/users")
app.include_router(payments.router)


Base.metadata.create_all(bind=engine)

# NOT MANDATORY
# @app.get("/")
# def root():
#     return {"message": "hello"}
