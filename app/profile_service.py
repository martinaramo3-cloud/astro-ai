from app.database import get_db_connection


def _row_to_profile(row) -> dict:
    """SQLite stores the flag as 0/1; the API contract says it's a boolean."""
    profile = dict(row)
    profile["birth_time_known"] = bool(profile.get("birth_time_known", 1))
    return profile


def create_profile(owner_user_id, label, person_name, relationship_type, birth_date, birth_time, birth_place, birth_time_known=True):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO profiles (
            owner_user_id, label, person_name, relationship_type,
            birth_date, birth_time, birth_place, birth_time_known
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        owner_user_id, label, person_name, relationship_type,
        birth_date, birth_time, birth_place, 1 if birth_time_known else 0
    ))

    conn.commit()
    profile_id = cursor.lastrowid

    cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    row = cursor.fetchone()
    conn.close()

    return _row_to_profile(row)

def list_profiles_by_owner(owner_user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM profiles
        WHERE owner_user_id = ?
        ORDER BY created_at DESC
    """, (owner_user_id,))

    rows = cursor.fetchall()
    conn.close()

    return [_row_to_profile(row) for row in rows]

def get_profile_by_id(profile_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    row = cursor.fetchone()
    conn.close()

    return _row_to_profile(row) if row else None

def delete_profile_by_id(profile_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted

EDITABLE_PROFILE_FIELDS = (
    "label", "person_name", "relationship_type",
    "birth_date", "birth_time", "birth_place", "birth_time_known",
)


def update_profile(profile_id: int, changes: dict):
    """Apply a partial update and return the saved row, or None if unknown.

    `relationship_type` is optional on the form, so an empty string is a real
    value here — clearing it is something the owner can legitimately do.
    """
    fields = {
        k: v for k, v in changes.items()
        if k in EDITABLE_PROFILE_FIELDS and v is not None
    }
    if not fields:
        return get_profile_by_id(profile_id)

    if "birth_time_known" in fields:
        fields["birth_time_known"] = 1 if fields["birth_time_known"] else 0

    assignments = ", ".join(f"{name} = ?" for name in fields)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE profiles SET {assignments} WHERE id = ?",
        (*fields.values(), profile_id),
    )
    conn.commit()
    conn.close()

    return get_profile_by_id(profile_id)
