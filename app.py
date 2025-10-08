"""Flask application for Industrial Data System using Supabase and Cloudinary."""
from __future__ import annotations

import os
from functools import wraps
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from supabase import Client, create_client
import cloudinary
import cloudinary.uploader

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be configured in environment variables."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me")


def login_required(view):
    """Decorator ensuring a user is authenticated before accessing a view."""

    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        if not current_user():
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def current_user() -> Optional[Dict[str, Any]]:
    """Return the currently authenticated user, refreshing the session if needed."""

    token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    if not token or not refresh_token:
        return None

    try:
        session_response = supabase.auth.set_session(token, refresh_token)
        response = supabase.auth.get_user(token)
    except Exception:
        session.clear()
        return None

    user = response.user if response else None
    if not user:
        session.clear()
        return None

    current_session = None
    if session_response and getattr(session_response, "session", None):
        current_session = session_response.session
    else:
        current_session = getattr(supabase.auth, "session", None)

    if current_session is not None:
        session["access_token"] = getattr(current_session, "access_token", token)
        session["refresh_token"] = getattr(current_session, "refresh_token", refresh_token)

    return {
        "id": getattr(user, "id", None),
        "email": getattr(user, "email", ""),
        "metadata": getattr(user, "user_metadata", {}) or {},
    }


@app.route("/")
@login_required
def dashboard():
    user = current_user()
    files: List[Dict[str, Any]] = []
    if user and user.get("id"):
        try:
            response = (
                supabase.table("files")
                .select("id, filename, url, created_at")
                .eq("user_id", user["id"])
                .order("created_at", desc=True)
                .execute()
            )
            files = response.data or []
        except Exception as exc:
            flash(f"Failed to load files from Supabase: {exc}", "danger")

    return render_template("dashboard.html", user=user, files=files)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")

        try:
            auth_response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:
            flash(f"Unable to sign in: {exc}", "danger")
            return render_template("login.html")

        if not getattr(auth_response, "session", None):
            flash("No active Supabase session returned.", "danger")
            return render_template("login.html")

        session["access_token"] = auth_response.session.access_token
        session["refresh_token"] = auth_response.session.refresh_token
        session["user_email"] = email

        flash("Signed in successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        # Ignore sign-out errors to ensure local session is cleared.
        pass
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Email is required to reset the password.", "danger")
            return render_template("forgot_password.html")

        try:
            supabase.auth.reset_password_email(email)
        except Exception as exc:
            flash(f"Failed to initiate password reset: {exc}", "danger")
            return render_template("forgot_password.html")

        flash("Password reset instructions have been sent if the email exists.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    user = current_user()
    if not user:
        flash("Session expired. Please sign in again.", "warning")
        return redirect(url_for("login"))

    file = request.files.get("file")
    if not file:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("dashboard"))

    try:
        upload_result = cloudinary.uploader.upload(file)
    except Exception as exc:
        flash(f"Cloudinary upload failed: {exc}", "danger")
        return redirect(url_for("dashboard"))

    file_url = upload_result.get("secure_url")
    if not file_url:
        flash("Cloudinary did not return a file URL.", "danger")
        return redirect(url_for("dashboard"))

    metadata = {
        "user_id": user.get("id"),
        "filename": file.filename,
        "url": file_url,
    }

    try:
        supabase.table("files").insert(metadata).execute()
    except Exception as exc:
        flash(f"Failed to store file metadata in Supabase: {exc}", "danger")
        return redirect(url_for("dashboard"))

    flash("File uploaded successfully.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
