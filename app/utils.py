import qrcode
import io
import base64
import smtplib
from email.message import EmailMessage
import os
import logging
import re
from .email_templates import base_email_template
from .models import EmailSettings, User, db

def generate_qr_code(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return f"data:image/png;base64,{qr_base64}"

def send_email(subject, html_content, to_email):
    """Send an email if credentials are configured.

    The function logs any exception and returns ``True`` on success and
    ``False`` if the email could not be sent. This prevents unexpected
    server errors when email credentials are missing or invalid.
    """

    msg = EmailMessage()
    msg['Subject'] = subject
    settings = EmailSettings.query.first()
    email_from = os.getenv('EMAIL_FROM')
    email_password = os.getenv('EMAIL_PASSWORD')
    if settings:
        if settings.email_from:
            email_from = settings.email_from
        if settings.email_password:
            email_password = settings.email_password

    msg['From'] = email_from
    msg['To'] = to_email
    msg.set_content("Ez egy HTML formátumú e-mail.")
    msg.add_alternative(html_content, subtype='html')

    if not email_from or not email_password:
        logging.error('Email credentials are not configured.')
        return False

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_from, email_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        logging.error('Failed to send email: %s', exc)
        return False


def send_event_email(event, subject, default_html, to_email):
    settings = EmailSettings.query.first()

    def _extract_content(html: str) -> str:
        """Return the text content from a ``base_email_template`` HTML string."""
        match = re.search(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
        return match.group(1) if match else ""

    default_content = _extract_content(default_html)

    if settings:
        mapping = {
            'user_created': (settings.user_created_enabled, settings.user_created_text),
            'user_deleted': (settings.user_deleted_enabled, settings.user_deleted_text),
            'pass_created': (settings.pass_created_enabled, settings.pass_created_text),
            'pass_deleted': (settings.pass_deleted_enabled, settings.pass_deleted_text),
            'pass_used': (settings.pass_used_enabled, settings.pass_used_text),
            'event_signup_user': (
                settings.event_signup_user_enabled,
                settings.event_signup_user_text,
            ),
            'event_signup_admin': (
                settings.event_signup_admin_enabled,
                settings.event_signup_admin_text,
            ),
            'event_unregister_user': (
                settings.event_unregister_user_enabled,
                settings.event_unregister_user_text,
            ),
            'event_unregister_admin': (
                settings.event_unregister_admin_enabled,
                settings.event_unregister_admin_text,
            ),
        }
        enabled, custom_text = mapping.get(event, (False, None))
        if not enabled:
            return False
        if custom_text:
            combined = f"{custom_text}<br><br>{default_content}"
            html = base_email_template(subject, combined)
        else:
            html = default_html
    else:
        html = default_html

    return send_email(subject, html, to_email)


def send_weekly_reminders(app):
    """Send weekly reminder emails to opted-in users."""
    with app.app_context():
        settings = EmailSettings.query.first()
        if not settings or not settings.weekly_reminder_enabled:
            return
        text = settings.weekly_reminder_text or "Emlékeztető"
        html = base_email_template("Heti emlékeztető", text)
        recipients = User.query.filter_by(weekly_reminder_opt_in=True).all()
        for user in recipients:
            send_email("Heti emlékeztető", html, user.email)
