from app.database import get_db_connection

def create_profile(owner_user_id, label, person_name, relationship_type, birth_date, birth_time, birth_place):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO profiles (
            owner_user_id, label, person_name, relationship_type,
            birth_date, birth_time, birth_place
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        owner_user_id, label, person_name, relationship_type,
        birth_date, birth_time, birth_place
    ))

    conn.commit()
    profile_id = cursor.lastrowid

    cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row)

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

    return [dict(row) for row in rows]

def get_profile_by_id(profile_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

def delete_profile_by_id(profile_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted