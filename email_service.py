"""
Email service module for West Hants Padel Matchmaker.
Sends verification emails via SMTP.

Configure via environment variables:
  SMTP_HOST     - SMTP server hostname (e.g. smtp.azurecomm.net)
  SMTP_PORT     - SMTP port (default: 587)
  SMTP_USER     - SMTP username / login
  SMTP_PASSWORD  - SMTP password or API key
  SMTP_FROM     - Sender email address (e.g. noreply@yourdomain.com)

When SMTP_HOST is not set, emails are printed to the console (dev mode).
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@westhants-padel.com")


def send_verification_email(to_email, first_name, code):
    """Send a 6-digit verification code to the user's email."""
    subject = "Verify your West Hants Padel account"
    html_body = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="font-size: 48px;">🏸</span>
            <h1 style="color: #1a5632; margin: 8px 0 4px;">West Hants Padel</h1>
        </div>
        <p>Hi {first_name or 'there'},</p>
        <p>Thanks for signing up! Enter this code in the app to verify your email:</p>
        <div style="text-align: center; margin: 32px 0;">
            <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #1a5632;
                         background: #f0f7f3; padding: 16px 32px; border-radius: 12px;
                         display: inline-block;">{code}</span>
        </div>
        <p style="color: #666; font-size: 14px;">This code expires in 15 minutes.</p>
        <p style="color: #666; font-size: 14px;">If you didn't create an account, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">The West Hants Club &middot; Bournemouth</p>
    </div>
    """
    text_body = (
        f"Hi {first_name or 'there'},\n\n"
        f"Your verification code is: {code}\n\n"
        f"This code expires in 15 minutes.\n\n"
        f"– West Hants Padel"
    )

    if not SMTP_HOST:
        # Dev mode – just print to console
        print(f"\n{'='*50}")
        print(f"  VERIFICATION EMAIL (dev mode)")
        print(f"  To:   {to_email}")
        print(f"  Code: {code}")
        print(f"{'='*50}\n")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        return False


def send_password_reset_email(to_email, first_name, code):
    """Send a 6-digit password reset code to the user's email."""
    subject = "Reset your West Hants Padel password"
    html_body = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="font-size: 48px;">\U0001f3f8</span>
            <h1 style="color: #1a5632; margin: 8px 0 4px;">West Hants Padel</h1>
        </div>
        <p>Hi {first_name or 'there'},</p>
        <p>We received a request to reset your password. Enter this code in the app:</p>
        <div style="text-align: center; margin: 32px 0;">
            <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #1a5632;
                         background: #f0f7f3; padding: 16px 32px; border-radius: 12px;
                         display: inline-block;">{code}</span>
        </div>
        <p style="color: #666; font-size: 14px;">This code expires in 15 minutes.</p>
        <p style="color: #666; font-size: 14px;">If you didn't request a password reset, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">The West Hants Club &middot; Bournemouth</p>
    </div>
    """
    text_body = (
        f"Hi {first_name or 'there'},\n\n"
        f"Your password reset code is: {code}\n\n"
        f"This code expires in 15 minutes.\n\n"
        f"If you didn't request this, please ignore this email.\n\n"
        f"\u2013 West Hants Padel"
    )

    if not SMTP_HOST:
        print(f"\n{'='*50}")
        print(f"  PASSWORD RESET EMAIL (dev mode)")
        print(f"  To:   {to_email}")
        print(f"  Code: {code}")
        print(f"{'='*50}\n")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        return False
