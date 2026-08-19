import csv
import io
import os
import sqlite3
from datetime import datetime
from functools import wraps

import requests
from flask import (
    Flask,
    Response,
    abort,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "submissions.db"))

# --- Admin credentials ---
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

# --- Email notification (Resend) ---
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "onboarding@resend.dev")

def half_hour_slots(start_hour, end_hour):
    """Build ['08:00', '08:30', ..., '18:00'] between two hours (inclusive)."""
    slots = []
    for hour in range(start_hour, end_hour + 1):
        slots.append(f"{hour:02d}:00")
        if hour != end_hour:
            slots.append(f"{hour:02d}:30")
    return slots


# Form field definitions: (db_column, label, input_type, required, options)
FIELDS = [
    ("date_visite", "Date de la visite", "date", True, None),
    ("heure_visite", "Heure de la visite", "select", True, half_hour_slots(8, 18)),
    ("acces_toilettes", "Besoin d'un accès aux toilettes municipales", "radio", True, ["Oui", "Non"]),
    ("acces_preau", "Besoin d'accès au préau pour la pause méridienne", "radio", True, ["Oui", "Non"]),
    ("nombre_enfants", "Nombre d'enfants (environ)", "number", True, None),
    ("nombre_vehicules", "Nombre de véhicules sur le parking", "number", False, None),
    ("nom_etablissement", "Nom de l'établissement", "text", True, None),
    ("niveau_scolaire", "Niveau scolaire", "text", False, None),
    ("commentaires", "Commentaires / questions", "textarea", False, None),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    columns = ",\n    ".join(f"{col} TEXT" for col, *_ in FIELDS)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            {columns}
        )
        """
    )
    # Lightweight migration: add any columns introduced after the table was first
    # created, so new FIELDS entries don't break inserts on an existing database.
    existing = {row[1] for row in conn.execute("PRAGMA table_info(submissions)")}
    for col, *_ in FIELDS:
        if col not in existing:
            conn.execute(f"ALTER TABLE submissions ADD COLUMN {col} TEXT")
    conn.commit()
    conn.close()


def send_notification(data):
    """Send an email via Resend when a form is submitted. Best-effort."""
    if not (RESEND_API_KEY and NOTIFY_EMAIL):
        return
    lines = [f"<b>{label}:</b> {data.get(col, '') or '—'}" for col, label, *_ in FIELDS]
    html = "<h2>Nouvelle demande de visite</h2>" + "<br>".join(lines)
    try:
        requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": FROM_EMAIL,
                "to": [NOTIFY_EMAIL],
                "subject": f"Nouvelle demande de visite — {data.get('nom_etablissement', '')}",
                "html": html,
            },
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001 — don't let email failure break submission
        app.logger.warning("Notification email failed: %s", exc)


@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        data = {}
        errors = []
        for col, label, _type, required, _options in FIELDS:
            value = (request.form.get(col) or "").strip()
            if required and not value:
                errors.append(label)
            data[col] = value
        if errors:
            return render_template(
                "form.html", fields=FIELDS, errors=errors, values=data
            )

        cols = ", ".join(col for col, *_ in FIELDS)
        placeholders = ", ".join("?" for _ in FIELDS)
        values = [data[col] for col, *_ in FIELDS]
        db = get_db()
        db.execute(
            f"INSERT INTO submissions (created_at, {cols}) VALUES (?, {placeholders})",
            [datetime.utcnow().isoformat(timespec="seconds")] + values,
        )
        db.commit()
        send_notification(data)
        return redirect(url_for("thanks"))

    return render_template("form.html", fields=FIELDS, errors=None, values={})


@app.route("/merci")
def thanks():
    return render_template("thanks.html")


# --- Admin ---
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)

    return wrapper


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (
            request.form.get("username") == ADMIN_USER
            and request.form.get("password") == ADMIN_PASSWORD
        ):
            session["logged_in"] = True
            return redirect(request.args.get("next") or url_for("admin"))
        error = "Identifiants incorrects."
    return render_template("login.html", error=error)


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
def admin():
    db = get_db()
    rows = db.execute("SELECT * FROM submissions ORDER BY id DESC").fetchall()
    return render_template("admin.html", rows=rows, fields=FIELDS)


@app.route("/admin/export.csv")
@login_required
def export_csv():
    db = get_db()
    rows = db.execute("SELECT * FROM submissions ORDER BY id DESC").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    header = ["id", "created_at"] + [label for _col, label, *_ in FIELDS]
    writer.writerow(header)
    for row in rows:
        writer.writerow(
            [row["id"], row["created_at"]] + [row[col] for col, *_ in FIELDS]
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=visites.csv"},
    )


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
