from fastapi import FastAPI
from app.routes import auth, slots, appointments
from app.database import Base, engine

app = FastAPI()

app.include_router(auth.router)
app.include_router(slots.router, prefix="/slots")
app.include_router(appointments.router, prefix="/appointments")


Base.metadata.create_all(bind=engine)

# NOT MANDATORY
# @app.get("/")
# def root():
#     return {"message": "hello"}
