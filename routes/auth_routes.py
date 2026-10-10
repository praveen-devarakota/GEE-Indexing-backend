
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Blueprint, jsonify, request, current_app
import jwt
from werkzeug.security import check_password_hash

from models.user_model import (
    create_user,
    find_user_by_email,
    find_user_by_id,
    serialize_user,
)

auth_bp = Blueprint("auth", __name__)

TOKEN_EXPIRY_HOURS = 24


def create_access_token(user_id):
    secret = os.getenv("JWT_SECRET")

    if not secret:
        raise RuntimeError("JWT_SECRET is not configured.")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }

    return jwt.encode(payload, secret, algorithm="HS256")


def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Authorization token is required."}), 401

        token = parts[1]
        secret = os.getenv("JWT_SECRET")

        if not secret:
            return jsonify({"error": "Authentication is not configured."}), 500

        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
            )
            user_id = payload.get("sub")

            if not user_id:
                return jsonify({"error": "Invalid token."}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Your session has expired. Please log in again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid authentication token."}), 401

        user = find_user_by_id(user_id)

        if not user:
            return jsonify({"error": "User not found."}), 401

        return func(user, *args, **kwargs)

    return wrapper


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not all(isinstance(value, str) for value in (name, email, password)):
        return jsonify({"error": "Name, email, and password are required."}), 400

    name = name.strip()
    email = email.strip().lower()

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required."}), 400

    if len(name) > 100 or len(email) > 254:
        return jsonify({"error": "Name or email is too long."}), 400

    if "@" not in email or email.startswith("@") or email.endswith("@"):
        return jsonify({"error": "Please provide a valid email address."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    try:
        user = create_user(name, email, password)

        if user is None:
            return jsonify({"error": "An account with this email already exists."}), 409

        access_token = create_access_token(str(user["_id"]))

        return jsonify({
            "access_token": access_token,
            "user": serialize_user(user),
        }), 201

    except Exception:
        current_app.logger.exception("Registration failed.")
        return jsonify({"error": "Registration failed. Please try again."}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Email and password are required."}), 400

    if not email.strip() or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        user = find_user_by_email(email)

        if not user or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({"error": "Invalid email or password."}), 401

        access_token = create_access_token(str(user["_id"]))

        return jsonify({
            "access_token": access_token,
            "user": serialize_user(user),
        }), 200

    except Exception:
        current_app.logger.exception("Login failed.")
        return jsonify({"error": "Login failed. Please try again."}), 500


@auth_bp.route("/profile", methods=["GET"])
@token_required
def profile(user):
    return jsonify({
        "user": serialize_user(user),
    }), 200
