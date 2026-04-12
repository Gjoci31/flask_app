from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    DateField,
    TimeField,
    IntegerField,
    SubmitField,
    SelectField,
    TextAreaField,
    BooleanField,
    FileField,
)
from wtforms.validators import DataRequired, NumberRange

class PassForm(FlaskForm):
    type = StringField('Típus', validators=[DataRequired()])
    start_date = DateField('Kezdő dátum', validators=[DataRequired()])
    end_date = DateField('Lejárati dátum', validators=[DataRequired()])
    total_uses = IntegerField('Alkalmak száma', validators=[DataRequired(), NumberRange(min=1)])
    user_id = SelectField('Felhasználó', coerce=int, validators=[DataRequired()])
    comment = TextAreaField('Megjegyzés')
    submit = SubmitField('Bérlet létrehozása')


class UserForm(FlaskForm):
    username = StringField('Felhasználónév', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = StringField('Jelszó', validators=[DataRequired()])
    role = SelectField('Szerep', choices=[('user', 'User'), ('admin', 'Admin')], validators=[DataRequired()])
    submit = SubmitField('Mentés')


class LoginForm(FlaskForm):
    username = StringField('Felhasználónév', validators=[DataRequired()])
    password = PasswordField('Jelszó', validators=[DataRequired()])
    submit = SubmitField('Bejelentkezés')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Jelszó elküldése')


class EmailSettingsForm(FlaskForm):
    email_from = StringField('Feladó email')
    email_password = PasswordField('Email jelszó')

    user_created_enabled = BooleanField('Felhasználó létrehozásakor')
    user_created_text = TextAreaField('Létrehozás üzenete')

    user_deleted_enabled = BooleanField('Felhasználó törlésekor')
    user_deleted_text = TextAreaField('Törlés üzenete')

    pass_created_enabled = BooleanField('Új bérlet létrehozásakor')
    pass_created_text = TextAreaField('Bérlet létrehozás üzenete')

    pass_deleted_enabled = BooleanField('Bérlet törlésekor')
    pass_deleted_text = TextAreaField('Bérlet törlés üzenete')

    pass_used_enabled = BooleanField('Alkalom változásakor')
    pass_used_text = TextAreaField('Alkalom változás üzenete')

    event_signup_user_enabled = BooleanField('Esemény jelentkezéskor (saját)')
    event_signup_user_text = TextAreaField('Saját jelentkezés üzenete')

    event_signup_admin_enabled = BooleanField('Esemény jelentkezéskor (admin)')
    event_signup_admin_text = TextAreaField('Admin jelentkeztetés üzenete')

    event_unregister_user_enabled = BooleanField('Leiratkozáskor (saját)')
    event_unregister_user_text = TextAreaField('Saját leiratkozás üzenete')

    event_unregister_admin_enabled = BooleanField('Leiratkozáskor (admin)')
    event_unregister_admin_text = TextAreaField('Admin leiratkoztatás üzenete')

    weekly_reminder_enabled = BooleanField('Heti emlékeztető bekapcsolása')
    weekly_reminder_text = TextAreaField('Emlékeztető szöveg')
    weekly_reminder_day = SelectField(
        'Emlékeztető napja',
        choices=[
            (0, 'Hétfő'),
            (1, 'Kedd'),
            (2, 'Szerda'),
            (3, 'Csütörtök'),
            (4, 'Péntek'),
            (5, 'Szombat'),
            (6, 'Vasárnap'),
        ],
        coerce=int,
    )
    weekly_reminder_time = TimeField('Emlékeztető időpontja')

    submit = SubmitField('Mentés')


class RestoreForm(FlaskForm):
    """Form used for uploading a database backup to restore."""
    backup_file = FileField('Backup fájl', validators=[DataRequired()])
    submit = SubmitField('Visszaállítás')


class EventForm(FlaskForm):
    name = StringField('Esemény neve', validators=[DataRequired()])
    date = DateField('Dátum', validators=[DataRequired()])
    start_time = TimeField('Kezdő időpont', validators=[DataRequired()])
    end_time = TimeField('Vég időpont', validators=[DataRequired()])
    capacity = IntegerField('Létszám', validators=[DataRequired(), NumberRange(min=1)])
    color = SelectField(
        'Szín',
        choices=[
            ('darkgreen', 'Sötétzöld'),
            ('red', 'Piros'),
            ('blue', 'Kék'),
            ('purple', 'Lila'),
            ('orange', 'Narancs'),
            ('burgundy', 'Bordó'),
            ('darkblue', 'Sötétkék'),
        ],
        default='blue',
        validators=[DataRequired()],
    )
    submit = SubmitField('Mentés')
