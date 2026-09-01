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