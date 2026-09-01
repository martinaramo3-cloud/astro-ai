from app.database import get_db_connection


def get_user_by_id(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row) 

# Only these can be changed after signup. Email and password are deliberately
# absent: both are credentials, and changing them needs its own confirmation
# flow rather than riding along with a birth-details edit.
EDITABLE_USER_FIELDS = ("name", "birth_date", "birth_time", "birth_place", "birth_time_known")


def update_user(user_id: int, changes: dict):
    """Apply a partial update and return the saved row, or None if unknown."""
    fields = {k: v for k, v in changes.items() if k in EDITABLE_USER_FIELDS and v is not None}
    if not fields:
        return get_user_by_id(user_id)

    if "birth_time_known" in fields:
        fields["birth_time_known"] = 1 if fields["birth_time_known"] else 0

    assignments = ", ".join(f"{name} = ?" for name in fields)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET {assignments} WHERE id = ?",
        (*fields.values(), user_id),
    )
    conn.commit()
    conn.close()

    return get_user_by_id(user_id)
