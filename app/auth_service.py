import os
import hashlib
import binascii
from app.database import get_db_connection


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000
    )
    return binascii.hexlify(salt).decode() + ":" + binascii.hexlify(hashed).decode()


def verify_password(password: str, stored_password: str) -> bool:
    salt_hex, hash_hex = stored_password.split(":")
    salt = binascii.unhexlify(salt_hex)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000
    )
    return binascii.hexlify(hashed).decode() == hash_hex


def create_account(name: str, email: str, password: str, birth_date: str, birth_time: str, birth_place: str, birth_time_known: bool = True):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()
        return None

    hashed_password = hash_password(password)

    cursor.execute("""
        INSERT INTO users (name, email, hashed_password, birth_date, birth_time, birth_place, birth_time_known, email_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
    """, (name, email, hashed_password, birth_date, birth_time, birth_place, 1 if birth_time_known else 0))

    conn.commit()

    user_id = cursor.lastrowid

    cursor.execute(
        "SELECT id, name, email, birth_date, birth_time, birth_place, "
        "birth_time_known, subscription_tier, email_verified FROM users WHERE id = ?",
        (user_id,),
    )
    user = cursor.fetchone()

    conn.close()
    return dict(user)


def login_user(email: str, password: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    conn.close()

    if not user:
        return None

    user = dict(user)

    if not verify_password(password, user["hashed_password"]):
        return None

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "birth_date": user["birth_date"],
        "birth_time": user["birth_time"],
        "birth_place": user["birth_place"],
        # Kept on the client so the chat and chart views know not to show a
        # Rising sign this account never supplied a time for.
        "birth_time_known": bool(user.get("birth_time_known", 1)),
        "subscription_tier": user.get("subscription_tier", "free"),
        "email_verified": bool(user.get("email_verified", 1)),
    }

def set_password(user_id: int, new_password: str) -> bool:
    """Replace a user's password with a fresh hash. Returns False if no such user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        return False
    cursor.execute(
        "UPDATE users SET hashed_password = ? WHERE id = ?",
        (hash_password(new_password), user_id),
    )
    conn.commit()
    conn.close()
    return True
