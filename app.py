import os
import sqlite3
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------
app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Secret key for sessions
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

# Upload directories
UPLOAD_ROOT = os.path.join(BASE_DIR, "static", "uploads")
IMAGE_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, "images")
VIDEO_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, "videos")

os.makedirs(IMAGE_UPLOAD_DIR, exist_ok=True)
os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}

# SQLite database for users
DATABASE = os.path.join(BASE_DIR, "users.db")


# ---------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create users table if it doesn't exist."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


# Initialize DB at startup
init_db()


# ---------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------
def allowed_file(filename: str, allowed_exts) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_exts


def login_required(view_func):
    """
    Decorator to protect routes. If not logged in, redirect to /login.
    """
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


# ---------------------------------------------------------------------
# Auth routes: register, login, logout
# ---------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Allow new users to create an account.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if not username or not password or not confirm:
            flash("Please fill in all fields.", "warning")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match.", "warning")
            return redirect(url_for("register"))

        # Basic length check
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "warning")
            return redirect(url_for("register"))

        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if existing:
            conn.close()
            flash("Username is already taken. Please choose another.", "warning")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        conn.close()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Log a user in using username/password from the SQLite DB.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """
    Log out current user and clear session.
    """
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------
# Core UI routes (protected)
# ---------------------------------------------------------------------
@app.route("/")
@login_required
def index():
    """
    Main dashboard:
    - Step 1: upload sketch/photo as query face
    - Step 2: upload CCTV/video to scan for that face
    """
    return render_template("index.html")


@app.route("/search-image", methods=["POST"])
@login_required
def search_image():
    """
    Handles sketch/photo upload.
    For now: returns DUMMY results to show how UI looks.
    Later: plug in actual facial recognition backend here.
    """
    file = request.files.get("query_image")

    if not file or file.filename == "":
        flash("Please choose a sketch or photo to upload.", "warning")
        return redirect(url_for("index"))

    if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        flash("Unsupported image type. Please upload a JPG or PNG.", "warning")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    save_path = os.path.join(IMAGE_UPLOAD_DIR, filename)
    file.save(save_path)

    # TODO: replace with real backend call using `save_path` as query image
    dummy_results = [
        {"label": "Person_A", "score": 0.23, "source": "suspect_ali_1.jpg"},
        {"label": "Person_B", "score": 0.41, "source": "suspect_maria_2.png"},
        {"label": "Unknown", "score": 0.68, "source": "unknown_3.png"},
    ]

    query_image_url = url_for("static", filename=f"uploads/images/{filename}")

    return render_template(
        "image_results.html",
        query_image=query_image_url,
        results=dummy_results,
    )


@app.route("/search-video", methods=["POST"])
@login_required
def search_video():
    """
    Handles CCTV/video upload.
    For now: returns DUMMY match timeline.
    Later: plug in actual frame-by-frame analysis using the query face.
    """
    file = request.files.get("video_file")

    if not file or file.filename == "":
        flash("Please choose a CCTV/video file to upload.", "warning")
        return redirect(url_for("index"))

    if not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        flash("Unsupported video type. Please upload MP4 / AVI / MOV / MKV.", "warning")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    save_path = os.path.join(VIDEO_UPLOAD_DIR, filename)
    file.save(save_path)

    # TODO: replace with real backend call using `save_path`
    dummy_matches = [
        {"time": "00:05", "label": "Person_A", "score": 0.27},
        {"time": "00:23", "label": "Person_B", "score": 0.35},
        {"time": "01:02", "label": "Unknown", "score": 0.62},
    ]

    return render_template(
        "video_results.html",
        video_name=filename,
        matches=dummy_matches,
    )


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Local development server.
    app.run(host="0.0.0.0", port=5000, debug=True)
