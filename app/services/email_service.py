
import os
from email.message import EmailMessage
import aiosmtplib


async def send_doctor_application_email(
    doctor_details: dict,
    review_url: str,
):
    sender = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    admin_email = os.getenv("DOCTOR_APPLICATION_ADMIN_EMAIL")

    if not sender or not password or not admin_email:
        raise RuntimeError("Email configuration is incomplete")

    message = EmailMessage()
    message["From"] = f"DocAppoint <{sender}>"
    message["To"] = admin_email
    message["Subject"] = "New Doctor Application - DocAppoint"

    message.set_content(
        f"""
A new doctor application has been submitted.

Name: {doctor_details['full_name']}
Specialization: {doctor_details['specialization']}
Qualification: {doctor_details['qualification']}
Registration Number: {doctor_details['registration_number']}
Clinic: {doctor_details['clinic_name']}
Clinic Address: {doctor_details['clinic_address']}
Consultation Fee: Rs. {doctor_details['consultation_fee']}
Experience: {doctor_details['experience_years']} years

Review this application:

{review_url}

These links expire after 48 hours.
"""
    )

    await aiosmtplib.send(
        message,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=sender,
        password=password,
    )
