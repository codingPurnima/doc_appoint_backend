
import os
import json
import base64
import asyncio
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _send_email(doctor_details: dict, review_url: str):
    token_json = os.getenv("GMAIL_TOKEN_JSON")
    sender = os.getenv("SMTP_EMAIL")
    admin_email = os.getenv("DOCTOR_APPLICATION_ADMIN_EMAIL")

    if not token_json or not sender or not admin_email:
        raise RuntimeError("Gmail configuration is incomplete")

    credentials = Credentials.from_authorized_user_info(
        json.loads(token_json),
        SCOPES,
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials.valid:
        raise RuntimeError("Gmail credentials are invalid or expired")

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )

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

This link expires after 48 hours.
"""
    )

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    service.users().messages().send(
        userId="me",
        body={"raw": encoded_message},
    ).execute()


async def send_doctor_application_email(
    doctor_details: dict,
    review_url: str,
):
    await asyncio.to_thread(
        _send_email,
        doctor_details,
        review_url,
    )
