from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..models import Event, EventRegistration, User, Pass, PassUsage, db
from ..forms import EventForm
from ..utils import send_email, send_event_email
from ..email_templates import (
    event_signup_user_email,
    event_signup_admin_email,
    event_unregister_user_email,
    event_unregister_admin_email,
    event_pass_deducted_user_email,
    event_activation_admin_email,
)


event_bp = Blueprint('events', __name__)
APP_TZ = ZoneInfo("Europe/Budapest")


def _now_local_naive():
    """Return the current local time as a naive datetime.

    Event timestamps are stored as naive local datetimes, so we compare
    against a naive "now" value in the same Europe/Budapest timezone.
    """
    return datetime.now(APP_TZ).replace(tzinfo=None)


def _get_two_week_range():
    start = _now_local_naive().date()
    end = start + timedelta(days=13)
    return start, end


def _get_usable_pass(user_id):
    today = _now_local_naive().date()
    return (
        Pass.query.filter(
            Pass.user_id == user_id,
            Pass.start_date <= today,
            Pass.end_date >= today,
            Pass.used < Pass.total_uses,
        )
        .order_by(Pass.end_date.asc(), Pass.id.asc())
        .first()
    )


@event_bp.route('/events')
@login_required
def events():
    start, end = _get_two_week_range()
    upcoming_events = (
        Event.query.filter(Event.start_time >= start, Event.start_time <= end)
        .order_by(Event.start_time)
        .all()
    )
    past_events = (
        Event.query.filter(Event.start_time < start)
        .order_by(Event.start_time.desc())
        .all()
    )
    days = [start + timedelta(days=i) for i in range(14)]
    events_map = {}
    for e in upcoming_events:
        day_idx = (e.start_time.date() - start).days
        start_hour = e.start_time.hour
        end_hour = e.end_time.hour
        for hour in range(start_hour, end_hour + 1):
            start_minute = e.start_time.minute if hour == start_hour else 0
            end_minute = e.end_time.minute if hour == end_hour else 60
            events_map.setdefault((day_idx, hour), []).append({
                'event': e,
                'start_minute': start_minute,
                'end_minute': end_minute,
                'is_first': hour == start_hour,
            })
    registrations = {
        reg.event_id: reg
        for reg in EventRegistration.query.filter_by(user_id=current_user.id)
    }

    participants = {
        e.id: "<br>".join(reg.user.username for reg in e.registrations) or "nincs"
        for e in (upcoming_events + past_events)
    }

    return render_template(
        'events.html',
        events=upcoming_events,
        past_events=past_events,
        start=start,
        end=end,
        registrations=registrations,
        days=days,
        events_map=events_map,
        participants=participants,
    )


@event_bp.route('/events/signup/<int:event_id>')
@login_required
def signup(event_id):
    event = Event.query.get_or_404(event_id)
    if event.spots_left <= 0:
        flash('Nincs szabad hely.', 'danger')
    elif EventRegistration.query.filter_by(event_id=event_id, user_id=current_user.id).first():
        flash('Már jelentkeztél erre az eseményre.', 'warning')
    else:
        reg = EventRegistration(event_id=event_id, user_id=current_user.id)
        db.session.add(reg)
        db.session.commit()
        send_event_email(
            'event_signup_user',
            'Esemény jelentkezés',
            event_signup_user_email(current_user.username, event),
            current_user.email,
        )
        flash('Jelentkezés sikeres.', 'success')
    return redirect(url_for('events.events'))


@event_bp.route('/events/unregister/<int:event_id>')
@login_required
def unregister(event_id):
    reg = EventRegistration.query.filter_by(event_id=event_id, user_id=current_user.id).first_or_404()
    event = reg.event
    deadline = event.start_time - timedelta(minutes=event.cancellation_deadline_minutes)
    if _now_local_naive() >= deadline:
        flash(
            'A leiratkozási határidő lejárt ennél az eseménynél.',
            'danger',
        )
        return redirect(url_for('events.events'))
    db.session.delete(reg)
    db.session.commit()
    send_event_email(
        'event_unregister_user',
        'Esemény leiratkozás',
        event_unregister_user_email(current_user.username, event),
        current_user.email,
    )
    flash('Jelentkezés törölve.', 'success')
    return redirect(url_for('events.events'))


@event_bp.route('/admin/events')
@login_required
def admin_events():
    if current_user.role != 'admin':
        return redirect(url_for('events.events'))
    events = (
        Event.query.order_by(Event.start_time.desc())
        .all()
    )
    users = User.query.all()
    return render_template('admin_events.html', events=events, users=users)


@event_bp.route('/admin/events/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if current_user.role != 'admin':
        return redirect(url_for('events.events'))
    form = EventForm()
    if form.validate_on_submit():
        start_dt = datetime.combine(form.date.data, form.start_time.data)
        end_dt = datetime.combine(form.date.data, form.end_time.data)
        event = Event(
            name=form.name.data,
            start_time=start_dt,
            end_time=end_dt,
            capacity=form.capacity.data,
            color=form.color.data,
            cancellation_deadline_minutes=form.cancellation_deadline_minutes.data,
        )
        db.session.add(event)
        db.session.commit()
        flash('Esemény létrehozva.', 'success')
        return redirect(url_for('events.admin_events'))
    return render_template('create_event.html', form=form)


@event_bp.route('/admin/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    """Edit an existing event."""
    if current_user.role != 'admin':
        return redirect(url_for('events.events'))

    event = Event.query.get_or_404(event_id)
    form = EventForm(obj=event)

    if request.method == 'GET':
        form.date.data = event.start_time.date()
        form.start_time.data = event.start_time.time()
        form.end_time.data = event.end_time.time()

    if form.validate_on_submit():
        event.start_time = datetime.combine(form.date.data, form.start_time.data)
        event.end_time = datetime.combine(form.date.data, form.end_time.data)
        event.capacity = form.capacity.data
        event.color = form.color.data
        event.cancellation_deadline_minutes = form.cancellation_deadline_minutes.data
        db.session.commit()
        flash('Esemény frissítve.', 'success')
        return redirect(url_for('events.admin_events'))

    users = User.query.all()
    return render_template('edit_event.html', form=form, event=event, users=users)


@event_bp.route('/admin/events/add_user/<int:event_id>', methods=['POST'])
@login_required
def add_user(event_id):
    if current_user.role != 'admin':
        return redirect(url_for('events.events'))
    user_id = request.form.get('user_id', type=int)
    event = Event.query.get_or_404(event_id)
    if event.spots_left <= 0:
        flash('Nincs szabad hely.', 'danger')
    elif EventRegistration.query.filter_by(event_id=event_id, user_id=user_id).first():
        flash('A felhasználó már jelentkezett.', 'warning')
    else:
        reg = EventRegistration(event_id=event_id, user_id=user_id)
        db.session.add(reg)
        db.session.commit()
        user = User.query.get(user_id)
        if user:
            send_event_email(
                'event_signup_admin',
                'Esemény jelentkezés',
                event_signup_admin_email(user.username, event),
                user.email,
            )
        flash('Felhasználó hozzáadva.', 'success')

    next_page = request.args.get('next')
    if next_page == 'edit':
        return redirect(url_for('events.edit_event', event_id=event_id))
    return redirect(url_for('events.admin_events', _anchor=f'event-{event_id}'))


@event_bp.route('/admin/events/remove_user/<int:event_id>/<int:user_id>', methods=['POST'])
@login_required
def remove_user(event_id, user_id):
    """Remove a user's registration from an event."""
    if current_user.role != 'admin':
        return redirect(url_for('events.events'))
    reg = EventRegistration.query.filter_by(event_id=event_id, user_id=user_id).first_or_404()
    event = reg.event
    user = reg.user
    db.session.delete(reg)
    db.session.commit()
    if user:
        send_event_email(
            'event_unregister_admin',
            'Esemény leiratkozás',
            event_unregister_admin_email(user.username, event),
            user.email,
        )
    flash('Felhasználó eltávolítva.', 'success')
    next_page = request.args.get('next')
    if next_page == 'edit':
        return redirect(url_for('events.edit_event', event_id=event_id))
    return redirect(url_for('events.admin_events', _anchor=f'event-{event_id}'))


@event_bp.route('/admin/events/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    """Delete an entire event."""
    if current_user.role != 'admin':
        return redirect(url_for('events.events'))
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Esemény törölve.', 'success')
    return redirect(url_for('events.admin_events', _anchor=f'event-{event_id}'))


@event_bp.route('/admin/events/<int:event_id>/activate')
@login_required
def activate_event(event_id):
    if current_user.role != 'admin':
        return redirect(url_for('events.events'))
    event = Event.query.get_or_404(event_id)
    event.is_activated = True
    db.session.commit()
    rows = []
    for reg in event.registrations:
        usable_pass = _get_usable_pass(reg.user_id)
        remaining = 0
        if usable_pass:
            remaining = usable_pass.total_uses - usable_pass.used
        rows.append({
            'user': reg.user,
            'pass_obj': usable_pass,
            'remaining': remaining,
            'charged': reg.charged,
        })
    return render_template('activate_event.html', event=event, rows=rows)


@event_bp.route('/admin/events/<int:event_id>/deduct', methods=['POST'])
@login_required
def deduct_event_passes(event_id):
    if current_user.role != 'admin':
        return redirect(url_for('events.events'))
    event = Event.query.get_or_404(event_id)
    lines = []
    processed = 0
    for reg in event.registrations:
        usable_pass = _get_usable_pass(reg.user_id)
        if reg.charged:
            lines.append(f"{reg.user.username}: már korábban levonva")
            continue
        if not usable_pass:
            lines.append(f"{reg.user.username}: nincs érvényes bérlet")
            continue
        usable_pass.used += 1
        usage = PassUsage(pass_id=usable_pass.id)
        db.session.add(usage)
        reg.charged = True
        reg.charged_at = _now_local_naive()
        processed += 1
        remaining = usable_pass.total_uses - usable_pass.used
        lines.append(
            f"{reg.user.username}: levonva ({usable_pass.type}), maradék: {remaining}"
        )
        send_event_email(
            'pass_used',
            'Bérlet levonás eseményhez',
            event_pass_deducted_user_email(reg.user.username, event, usable_pass.type, remaining),
            reg.user.email,
        )
    event.deductions_processed = True
    db.session.commit()

    admin_emails = [u.email for u in User.query.filter_by(role='admin').all() if u.email]
    for email in admin_emails:
        send_email(
            f'Levonás lista - {event.name}',
            event_activation_admin_email(event, lines),
            email,
        )

    flash(f'Levonás kész. Sikeres levonások: {processed}.', 'success')
    return redirect(url_for('events.activate_event', event_id=event.id))
