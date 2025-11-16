import os
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

# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Secret key for sessions (use env var in production)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

# Upload directories
UPLOAD_ROOT = os.path.join(BASE_DIR, "static", "uploads")
IMAGE_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, "images")
VIDEO_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, "videos")

os.makedirs(IMAGE_UPLOAD_DIR, exist_ok=True)
os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}

# -----------------------------------------------------------------------------
# Simple login config (demo only)
# -----------------------------------------------------------------------------
# In real production, you'd use a database and hashed passwords.
LOGIN_USERNAME = "admin"
LOGIN_PASSWORD = "sketchy123"  # change this for your demo


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def allowed_file(filename: str, allowed_exts) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_exts


def login_required(view_func):
    """
    Decorator to protect routes. If not logged in, redirect to /login.
    """
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


# -----------------------------------------------------------------------------
# Authentication routes
# -----------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Simple login page for Sketchy.
    Demo credentials: admin / sketchy123
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == LOGIN_USERNAME and password == LOGIN_PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """
    Log out current user and clear session.
    """
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# -----------------------------------------------------------------------------
# Core UI routes (protected)
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Local development server.
    # Others on the same network can access with: http://YOUR_IP:5000
    app.run(host="0.0.0.0", port=5000, debug=True)
