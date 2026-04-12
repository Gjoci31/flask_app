def base_email_template(title: str, content: str) -> str:
    return f"""
    <html>
      <body style='font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;'>
        <div style='max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 8px;'>
          <h2 style='color: #2c3e50;'>{title}</h2>
          <p style='color: #333;'>{content}</p>
          <hr>
          <small style='color: #999;'>Ez egy automatikus üzenet a Bérletkezelő Rendszertől.</small>
        </div>
      </body>
    </html>
    """

def registration_email(username: str, password: str) -> str:
    content = f"Kedves {username},<br><br>Felhasználónév: {username}<br>Jelszó: {password}<br>"
    return base_email_template("Fiók létrehozva", content)


def forgot_password_email(username: str, password: str) -> str:
    content = (
        f"Kedves {username},<br><br>"
        f"A kért jelszó: {password}<br>"
    )
    return base_email_template("Elfelejtett jelszó", content)

def _pass_details(p) -> str:
    """Return a HTML snippet describing the given ``Pass``."""
    comment = f"<br>Megjegyzés: {p.comment}" if p.comment else ""
    return (
        f"Bérlet típusa: {p.type}<br>"
        f"Érvényesség: {p.start_date} - {p.end_date}<br>"
        f"Felhasználás: {p.used}/{p.total_uses}{comment}"
    )


def pass_created_email(p) -> str:
    """Return the email HTML for a newly created pass."""
    return base_email_template("Új bérlet létrehozva", _pass_details(p))

def pass_deleted_email(username: str, pass_type: str, start, end, used) -> str:
    content = f"Törölt bérlet: {pass_type}<br>{start} - {end}<br>Felhasználva: {used} alkalom"
    return base_email_template("Bérlet törölve", content)


def pass_used_email(p) -> str:
    """Return the email HTML when a pass usage changes."""
    remaining = p.total_uses - p.used
    content = (
        f"Kedves {p.user.username},<br>"
        f"Felhasználtál egy alkalmat a(z) {p.type} bérletedből.<br>"
        f"Hátralévő alkalmak: {remaining}.<br><br>"
        f"{_pass_details(p)}"
    )
    return base_email_template("Bérlet használat", content)


def pass_usage_reverted_email(p) -> str:
    """Return the email HTML when a pass usage is undone."""
    remaining = p.total_uses - p.used
    content = (
        f"Kedves {p.user.username},<br>"
        f"Visszakaptál egy alkalmat a(z) {p.type} bérletedbe.<br>"
        f"Hátralévő alkalmak: {remaining}.<br><br>"
        f"{_pass_details(p)}"
    )
    return base_email_template("Bérlethasználat visszavonva", content)


def _event_details(e) -> str:
    """Return a HTML snippet describing an ``Event``."""
    return (
        f"Esemény: {e.name}<br>"
        f"Időpont: {e.formatted_time}"
    )


def event_signup_user_email(username: str, e) -> str:
    content = (
        f"Kedves {username},<br><br>"
        f"Sikeresen jelentkeztél a következő eseményre:<br>"
        f"{_event_details(e)}"
    )
    return base_email_template("Esemény jelentkezés", content)


def event_signup_admin_email(username: str, e) -> str:
    content = (
        f"Kedves {username},<br><br>"
        f"Az admin regisztrált a következő eseményre:<br>"
        f"{_event_details(e)}"
    )
    return base_email_template("Esemény jelentkezés", content)


def event_unregister_user_email(username: str, e) -> str:
    """Return the email HTML when a user unregisters from an event."""
    content = (
        f"Kedves {username},<br><br>"
        f"Sikeresen leiratkoztál a következő eseményről:<br>"
        f"{_event_details(e)}"
    )
    return base_email_template("Esemény leiratkozás", content)


def event_unregister_admin_email(username: str, e) -> str:
    """Return the email HTML when an admin removes a user from an event."""
    content = (
        f"Kedves {username},<br><br>"
        f"Az admin törölte a jelentkezésed a következő eseményről:<br>"
        f"{_event_details(e)}"
    )
    return base_email_template("Esemény leiratkozás", content)
