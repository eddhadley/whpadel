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


def _send_email(to_email, subject, html_body, text_body):
    """Generic email sender used by notification functions."""
    if not SMTP_HOST:
        print(f"\n{'='*50}")
        print(f"  NOTIFICATION EMAIL (dev mode)")
        print(f"  To:      {to_email}")
        print(f"  Subject: {subject}")
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
        print(f"[EMAIL ERROR] Failed to send notification to {to_email}: {e}")
        return False


def _email_wrapper(content_html, content_text):
    """Wrap content in the standard West Hants Padel email template."""
    html = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="font-size: 48px;">\U0001f3f8</span>
            <h1 style="color: #1a5632; margin: 8px 0 4px;">West Hants Padel</h1>
        </div>
        {content_html}
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            The West Hants Club &middot; Bournemouth<br>
            <span style="color:#bbb">You received this because you enabled notifications. You can turn them off in your profile settings.</span>
        </p>
    </div>
    """
    text = f"{content_text}\n\n-- West Hants Padel\n(You can disable notifications in your profile settings.)"
    return html, text


def send_new_game_notification(to_email, first_name, creator_name, game_date, start_time, court, level_range):
    """Notify a user that a new game matching their skill level has been created."""
    subject = f"New padel game on {game_date} at {start_time}"
    content_html = f"""
        <p>Hi {first_name or 'there'},</p>
        <p>A new game has been posted that matches your skill level!</p>
        <div style="background: #f0f7f3; border-radius: 12px; padding: 16px; margin: 16px 0;">
            <div style="font-weight: 700; color: #1a5632; font-size: 16px; margin-bottom: 8px;">{court}</div>
            <div style="margin-bottom: 4px;">\U0001f4c5 {game_date} at {start_time}</div>
            <div style="margin-bottom: 4px;">\U0001f3be Level: {level_range}</div>
            <div>\U0001f464 Created by {creator_name}</div>
        </div>
        <p>Open the app to join!</p>
    """
    content_text = (
        f"Hi {first_name or 'there'},\n\n"
        f"A new game matching your skill level has been posted!\n\n"
        f"  Court: {court}\n"
        f"  Date: {game_date} at {start_time}\n"
        f"  Level: {level_range}\n"
        f"  Created by: {creator_name}\n\n"
        f"Open the app to join!"
    )
    html, text = _email_wrapper(content_html, content_text)
    return _send_email(to_email, subject, html, text)


def send_player_joined_notification(to_email, first_name, joiner_name, game_date, start_time, court, player_count, max_players):
    """Notify the game creator that someone joined their game."""
    subject = f"{joiner_name} joined your padel game"
    content_html = f"""
        <p>Hi {first_name or 'there'},</p>
        <p><strong>{joiner_name}</strong> has joined your game!</p>
        <div style="background: #f0f7f3; border-radius: 12px; padding: 16px; margin: 16px 0;">
            <div style="font-weight: 700; color: #1a5632; font-size: 16px; margin-bottom: 8px;">{court}</div>
            <div style="margin-bottom: 4px;">\U0001f4c5 {game_date} at {start_time}</div>
            <div>\U0001f465 Players: {player_count}/{max_players}</div>
        </div>
    """
    content_text = (
        f"Hi {first_name or 'there'},\n\n"
        f"{joiner_name} has joined your game!\n\n"
        f"  Court: {court}\n"
        f"  Date: {game_date} at {start_time}\n"
        f"  Players: {player_count}/{max_players}"
    )
    html, text = _email_wrapper(content_html, content_text)
    return _send_email(to_email, subject, html, text)


def send_game_reminder(to_email, first_name, game_date, start_time, court, player_count, max_players):
    """Send a 24-hour reminder for an upcoming game."""
    subject = f"Reminder: Padel game tomorrow at {start_time}"
    content_html = f"""
        <p>Hi {first_name or 'there'},</p>
        <p>Just a reminder that you have a padel game coming up tomorrow!</p>
        <div style="background: #f0f7f3; border-radius: 12px; padding: 16px; margin: 16px 0;">
            <div style="font-weight: 700; color: #1a5632; font-size: 16px; margin-bottom: 8px;">{court}</div>
            <div style="margin-bottom: 4px;">\U0001f4c5 {game_date} at {start_time}</div>
            <div>\U0001f465 Players: {player_count}/{max_players}</div>
        </div>
        <p>See you on court! \U0001f3be</p>
    """
    content_text = (
        f"Hi {first_name or 'there'},\n\n"
        f"Reminder: You have a padel game tomorrow!\n\n"
        f"  Court: {court}\n"
        f"  Date: {game_date} at {start_time}\n"
        f"  Players: {player_count}/{max_players}\n\n"
        f"See you on court!"
    )
    html, text = _email_wrapper(content_html, content_text)
    return _send_email(to_email, subject, html, text)
