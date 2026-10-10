
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash

from config.database import get_database


def get_users_collection():
    return get_database()["users"]


def create_user(name, email, password):
    users = get_users_collection()

    # Ensure email addresses are unique.
    users.create_index("email", unique=True)

    user = {
        "name": name.strip(),
        "email": email.strip().lower(),
        "password_hash": generate_password_hash(password),
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = users.insert_one(user)
        user["_id"] = result.inserted_id
        return user
    except DuplicateKeyError:
        return None


def find_user_by_email(email):
    return get_users_collection().find_one({
        "email": email.strip().lower()
    })


def find_user_by_id(user_id):
    if not ObjectId.is_valid(user_id):
        return None

    return get_users_collection().find_one({
        "_id": ObjectId(user_id)
    })


def verify_password(user, password):
    return check_password_hash(user["password_hash"], password)


def serialize_user(user):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
    }
