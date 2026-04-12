from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    send_file,
    current_app,
)
from flask_login import login_required, current_user
import os
import shutil

from ..models import Pass, PassUsage, User, db, EmailSettings
from ..forms import PassForm, UserForm, EmailSettingsForm, RestoreForm
from ..utils import send_event_email
from .. import update_weekly_reminder_schedule
from ..email_templates import (
    pass_created_email,
    pass_deleted_email,
    pass_used_email,
    pass_usage_reverted_email,
    registration_email,
    base_email_template,
)
from datetime import date

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/create_pass', methods=['GET', 'POST'])
@login_required
def create_pass():
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    form = PassForm()
    users = User.query.all()
    form.user_id.choices = [(u.id, u.username) for u in users]

    if form.validate_on_submit():
        new_pass = Pass(
            type=form.type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            total_uses=form.total_uses.data,
            used=0,
            comment=form.comment.data,
            user_id=form.user_id.data
        )
        db.session.add(new_pass)
        db.session.commit()
        send_event_email(
            'pass_created',
            "Új bérlet",
            pass_created_email(new_pass),
            new_pass.user.email
        )
        flash("Bérlet sikeresen létrehozva.", "success")
        return redirect(url_for('user.dashboard'))

    return render_template('create_pass.html', form=form)


@admin_bp.route('/extend_pass/<int:pass_id>', methods=['GET', 'POST'])
@login_required
def extend_pass(pass_id):
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    p = Pass.query.get_or_404(pass_id)
    form = PassForm(obj=p)
    users = User.query.all()
    form.user_id.choices = [(u.id, u.username) for u in users]
    if form.validate_on_submit():
        p.type = form.type.data
        p.start_date = form.start_date.data
        p.end_date = form.end_date.data
        p.total_uses = form.total_uses.data
        p.comment = form.comment.data
        p.user_id = form.user_id.data
        db.session.commit()
        send_email(
            "Bérlet hosszabbítva",
            pass_created_email(p),
            p.user.email,
        )
        flash("Bérlet módosítva.", "success")
        return redirect(url_for('admin.verify_pass', pass_id=p.id))

    return render_template('extend_pass.html', form=form, pass_id=pass_id, p=p)

@admin_bp.route('/delete_pass/<int:pass_id>')
@login_required
def delete_pass(pass_id):
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    selected_pass = Pass.query.get_or_404(pass_id)
    # collect details before deleting because the instance will be detached from
    # the session after deletion and commit
    user_name = selected_pass.user.username
    user_email = selected_pass.user.email
    pass_type = selected_pass.type
    start_date = selected_pass.start_date
    end_date = selected_pass.end_date
    used = selected_pass.used

    db.session.delete(selected_pass)
    db.session.commit()
    send_event_email(
        'pass_deleted',
        "Bérlet törölve",
        pass_deleted_email(user_name, pass_type, start_date, end_date, used),
        user_email,
    )
    flash("Bérlet törölve.", "success")
    return redirect(url_for('user.dashboard'))


@admin_bp.route('/verify_pass/<int:pass_id>')
@login_required
def verify_pass(pass_id):
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    p = Pass.query.get_or_404(pass_id)
    today = date.today()
    return render_template('verify_pass.html', p=p, today=today)


@admin_bp.route('/use_pass/<int:pass_id>')
@login_required
def use_pass(pass_id):
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    p = Pass.query.get_or_404(pass_id)
    if p.used < p.total_uses and p.end_date >= date.today():
        p.used += 1
        usage = PassUsage(pass_id=pass_id)
        db.session.add(usage)
        db.session.commit()
        send_event_email(
            'pass_used',
            "Bérlet használat",
            pass_used_email(p),
            p.user.email,
        )
        flash("Alkalom hozzáadva.", "success")
    else:
        flash("A bérlet nem használható.", "danger")
    return redirect(url_for('admin.verify_pass', pass_id=pass_id))


@admin_bp.route('/undo_use/<int:pass_id>')
@login_required
def undo_use(pass_id):
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    p = Pass.query.get_or_404(pass_id)
    if p.used > 0:
        p.used -= 1
        last_usage = (
            PassUsage.query.filter_by(pass_id=pass_id)
            .order_by(PassUsage.used_on.desc())
            .first()
        )
        if last_usage:
            db.session.delete(last_usage)
        db.session.commit()
        send_event_email(
            'pass_used',
            "Bérlet használat visszavonva",
            pass_usage_reverted_email(p),
            p.user.email,
        )
        flash("Felhasználás visszavonva.", "success")
    return redirect(url_for('admin.verify_pass', pass_id=pass_id))


@admin_bp.route('/users')
@login_required
def users():
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))
    users = User.query.all()
    return render_template('users.html', users=users)


@admin_bp.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    form = UserForm()
    if form.validate_on_submit():
        # Prevent ``IntegrityError`` by ensuring the username and email are
        # unique before creating the user.
        if User.query.filter_by(email=form.email.data).first():
            flash("Az email cím már használatban van.", "danger")
            return render_template("create_user.html", form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash("A felhasználónév már foglalt.", "danger")
            return render_template("create_user.html", form=form)

        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        send_event_email(
            'user_created',
            "Felhasználó létrehozva",
            registration_email(user.username, form.password.data),
            user.email,
        )
        flash("Felhasználó létrehozva.", "success")
        return redirect(url_for('admin.users'))

    return render_template('create_user.html', form=form)


@admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Modify an existing user's details and password."""
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if request.method == 'GET':
        form.password.data = ''

    if form.validate_on_submit():
        # Ensure unique email and username when editing
        if User.query.filter(User.id != user_id, User.email == form.email.data).first():
            flash("Az email cím már használatban van.", "danger")
            return render_template("edit_user.html", form=form)
        if User.query.filter(User.id != user_id, User.username == form.username.data).first():
            flash("A felhasználónév már foglalt.", "danger")
            return render_template("edit_user.html", form=form)

        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.set_password(form.password.data)
        db.session.commit()
        flash("Felhasználó módosítva.", "success")
        return redirect(url_for('admin.users'))

    return render_template('edit_user.html', form=form)


@admin_bp.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))
    user = User.query.get_or_404(user_id)

    if user.username == 'admin':
        flash('Az admin felhasználó nem törölhető.', 'danger')
        return redirect(url_for('admin.users'))

    # Store details for the notification before the instance is removed
    username = user.username
    user_email = user.email

    db.session.delete(user)
    db.session.commit()
    send_event_email(
        'user_deleted',
        "Felhasználó törölve",
        base_email_template("Felhasználó törölve", f"{username} törölve."),
        user_email,
    )
    flash("Felhasználó törölve.", "success")
    return redirect(url_for('admin.users'))


@admin_bp.route('/email_settings', methods=['GET', 'POST'])
@login_required
def email_settings():
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    settings = EmailSettings.query.first()
    if not settings:
        settings = EmailSettings()
        db.session.add(settings)
        db.session.commit()

    form = EmailSettingsForm(obj=settings)
    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        update_weekly_reminder_schedule(current_app)
        flash("Beállítások mentve.", "success")
        return redirect(url_for('user.dashboard'))

    return render_template('email_settings.html', form=form)


@admin_bp.route('/backup')
@login_required
def backup():
    """Download a backup of the database file."""
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    instance_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'instance'))
    db_file = os.path.join(instance_dir, 'passes.db')
    if not os.path.exists(db_file):
        flash('Nincs adatbázis a mentéshez.', 'danger')
        return redirect(url_for('admin.email_settings'))

    return send_file(db_file, as_attachment=True, download_name='passes_backup.db')


@admin_bp.route('/restore', methods=['GET', 'POST'])
@login_required
def restore():
    """Restore the database from an uploaded backup file."""
    if current_user.role != 'admin':
        return redirect(url_for('user.dashboard'))

    form = RestoreForm()
    if form.validate_on_submit():
        uploaded = form.backup_file.data
        if uploaded:
            instance_dir = os.path.abspath(os.path.join(current_app.root_path, '..', 'instance'))
            os.makedirs(instance_dir, exist_ok=True)
            db_file = os.path.join(instance_dir, 'passes.db')
            db.session.remove()
            db.engine.dispose()
            uploaded.save(db_file)
            flash('Adatbázis visszaállítva.', 'success')
            return redirect(url_for('admin.email_settings'))
        flash('Nem megfelelő fájl.', 'danger')

    return render_template('restore.html', form=form)
