from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from ..models import User, PendingRegistration
from werkzeug.security import check_password_hash, generate_password_hash
from ..forms import LoginForm, ForgotPasswordForm, RegistrationForm
from ..utils import send_email
from ..email_templates import forgot_password_email, base_email_template
from .. import db
import secrets
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.username.data.strip()
        password = form.password.data

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('user.dashboard'))
        flash('Hibás felhasználónév vagy jelszó.')
    return render_template('login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        if User.query.filter_by(email=email).first():
            flash('Ez az email cím már használatban van.', 'danger')
            return render_template('register.html', form=form)

        pending = PendingRegistration.query.filter_by(email=email).first()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        if pending:
            pending.password_hash = generate_password_hash(password)
            pending.password_plain = password
            pending.token = token
            pending.expires_at = expires_at
        else:
            pending = PendingRegistration(
                email=email,
                password_hash=generate_password_hash(password),
                password_plain=password,
                token=token,
                expires_at=expires_at,
            )
            db.session.add(pending)
        db.session.commit()

        verify_link = url_for('auth.verify_registration', token=token, _external=True)
        html = base_email_template(
            "Regisztráció megerősítése",
            (
                "Kérjük erősítsd meg a regisztrációt az alábbi linkre kattintva:<br>"
                f"<a href='{verify_link}'>{verify_link}</a><br><br>"
                "A link 24 óráig érvényes."
            ),
        )
        send_email("Regisztráció megerősítése", html, email)
        flash('Megerősítő email elküldve.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)


@auth_bp.route('/verify-registration/<token>')
def verify_registration(token):
    pending = PendingRegistration.query.filter_by(token=token).first()
    if not pending:
        flash('Érvénytelen megerősítő link.', 'danger')
        return redirect(url_for('auth.login'))
    if pending.expires_at < datetime.utcnow():
        db.session.delete(pending)
        db.session.commit()
        flash('A megerősítő link lejárt.', 'danger')
        return redirect(url_for('auth.register'))

    base_username = pending.email.split('@')[0]
    username = base_username
    idx = 1
    while User.query.filter_by(username=username).first():
        idx += 1
        username = f"{base_username}{idx}"

    user = User(
        username=username,
        email=pending.email,
        password_hash=pending.password_hash,
        password_plain=pending.password_plain,
        role='user',
    )
    db.session.add(user)
    db.session.delete(pending)
    db.session.commit()
    flash('A fiók létrejött, most már bejelentkezhetsz.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Send the user's existing password to the provided email."""
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            password = user.password_plain
            if not password:
                password = secrets.token_urlsafe(8)
                user.set_password(password)
                db.session.commit()
            send_email(
                "Elfelejtett jelszó",
                forgot_password_email(user.username, password),
                user.email,
            )
            flash('Jelszó elküldve az email címre.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Nem található felhasználó ezzel az email címmel.', 'danger')
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))
