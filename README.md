# DocAppoint - Backend
Backend API for the Doctor Appointment Booking System built using FastAPI.

## Tech Stack
- FastAPI
- Python
- SQLAlchemy
- MySQL
- JWT Authentication
- Uvicorn

## Features
- User Registration (Doctor / Patient)
- Secure Login using JWT
- Role-based authorization
- Slot creation for doctors
- Appointment booking by patients
- Appointment cancellation by patients
- Doctors can mark appointments as completed
- Prevents double booking of slots (concurrency control)

## Project Structure
``` text
app/
 ├── models/        # SQLAlchemy models
 ├── routes/        # API endpoints
 ├── schemas/       # Pydantic schemas
 ├── core/          # auth and config
 ├── database.py    # DB connection
 ├── main.py        # FastAPI entry point
```
## API Endpoints

### Authentication
- POST /register 
- POST /register/doctor
- POST /login  
- POST /auth/refresh

### Slots
- POST /slots/generate
- GET /slots
- GET /slots/available
- PATCH /slots/{slot_id}/freeze

### Appointments
- POST /appointments/book 
- PATCH /appointments/{id}/complete 
- GET /appointments/me
- GET /appointments/doctor
- PUT /appointments/{appointment_id}/cancel

### User
- GET /users/me

## Installation

Clone the repository:

git clone https://github.com/codingPurnima/doc_appoint_backend

Navigate into the folder:

cd app

Create virtual environment:

python -m venv env

Activate environment:

Windows:
env\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Run the server:

uvicorn main:app --reload

Server runs at:

https://doc-appoint-backend-meb4.onrender.com

Swagger docs:

https://doc-appoint-backend-meb4.onrender.com

## Frontend Repository
Frontend for this project is available here:

https://github.com/codingPurnima/doc_appoint_frontend
