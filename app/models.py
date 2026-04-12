from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    # Store the plain password for reminder emails. This is insecure but
    # required for the current application logic.
    password_plain = db.Column(db.String(150))
    role = db.Column(db.String(10), nullable=False, default='user')  # 'admin' or 'user'
    # Delete associated passes when a user is removed so foreign key
    # constraints don't raise an ``IntegrityError``.
    passes = db.relationship(
        'Pass', backref='user', lazy=True, cascade='all, delete-orphan'
    )
    event_registrations = db.relationship(
        'EventRegistration', backref='user', lazy=True, cascade='all, delete-orphan'
    )

    weekly_reminder_opt_in = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.password_plain = password

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Pass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.Date, nullable=False)
    total_uses = db.Column(db.Integer, nullable=False)
    used = db.Column(db.Integer, default=0)
    comment = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    usages = db.relationship(
        'PassUsage', backref='pass_ref', lazy=True, cascade='all, delete-orphan'
    )


class PassUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pass_id = db.Column(db.Integer, db.ForeignKey('pass.id'), nullable=False)
    used_on = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class EmailSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_from = db.Column(db.String(150))
    email_password = db.Column(db.String(150))

    user_created_enabled = db.Column(db.Boolean, default=False)
    user_created_text = db.Column(db.Text)

    user_deleted_enabled = db.Column(db.Boolean, default=False)
    user_deleted_text = db.Column(db.Text)

    pass_created_enabled = db.Column(db.Boolean, default=False)
    pass_created_text = db.Column(db.Text)

    pass_deleted_enabled = db.Column(db.Boolean, default=False)
    pass_deleted_text = db.Column(db.Text)

    pass_used_enabled = db.Column(db.Boolean, default=False)
    pass_used_text = db.Column(db.Text)

    event_signup_user_enabled = db.Column(db.Boolean, default=False)
    event_signup_user_text = db.Column(db.Text)

    event_signup_admin_enabled = db.Column(db.Boolean, default=False)
    event_signup_admin_text = db.Column(db.Text)

    event_unregister_user_enabled = db.Column(db.Boolean, default=False)
    event_unregister_user_text = db.Column(db.Text)

    event_unregister_admin_enabled = db.Column(db.Boolean, default=False)
    event_unregister_admin_text = db.Column(db.Text)

    weekly_reminder_enabled = db.Column(db.Boolean, default=False)
    weekly_reminder_text = db.Column(db.Text)
    weekly_reminder_day = db.Column(db.Integer, default=0)
    weekly_reminder_time = db.Column(db.Time)


class Event(db.Model):
    """Calendar event which users can sign up for."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(20), nullable=False, default='blue')
    registrations = db.relationship(
        'EventRegistration', backref='event', lazy=True, cascade='all, delete-orphan'
    )

    COLOR_MAP = {
        'darkgreen': '#006400',
        'red': '#dc3545',
        'blue': '#0d6efd',
        'purple': '#6f42c1',
        'orange': '#fd7e14',
        'burgundy': '#800020',
        'darkblue': '#00008b',
    }

    @property
    def color_hex(self) -> str:
        """Return the hex color code for the event's color."""
        return self.COLOR_MAP.get(self.color, '#0d6efd')

    @property
    def spots_left(self) -> int:
        return self.capacity - len(self.registrations)

    @property
    def formatted_time(self) -> str:
        """Return the event time formatted with the Hungarian day name."""
        day_names = [
            'Hétfő',
            'Kedd',
            'Szerda',
            'Csütörtök',
            'Péntek',
            'Szombat',
            'Vasárnap',
        ]
        start = self.start_time
        end = self.end_time
        return (
            f"{start.strftime('%Y-%m-%d')} "
            f"{day_names[start.weekday()]} "
            f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
        )

    @property
    def status(self) -> str:
        """Return whether the event is past, ongoing or upcoming."""
        now = datetime.now()
        if self.end_time < now:
            return "past"
        if self.start_time <= now <= self.end_time:
            return "ongoing"
        return "upcoming"


class EventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # ``User.event_registrations`` already adds a backref named ``user``
    # so defining another relationship with the same name causes a
    # ``sqlalchemy.exc.ArgumentError`` during mapper configuration.  The
    # backref automatically provides the ``user`` attribute on
    # ``EventRegistration`` instances, so the explicit relationship here is
    # unnecessary and leads to conflicts when the models are imported.


