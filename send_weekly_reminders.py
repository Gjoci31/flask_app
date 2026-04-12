from datetime import datetime
from zoneinfo import ZoneInfo

from app import create_app
from app.models import EmailSettings
from app.utils import send_weekly_reminders

app = create_app()

with app.app_context():
    settings = EmailSettings.query.first()
    if (
        settings
        and settings.weekly_reminder_enabled
        and settings.weekly_reminder_day
        == datetime.now(ZoneInfo("Europe/Budapest")).weekday()
    ):
        send_weekly_reminders(app)
