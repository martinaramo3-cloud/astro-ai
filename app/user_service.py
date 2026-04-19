from app.database import get_db_connection


def create_user(name: str, birth_date: str, birth_time: str, birth_place: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (name, birth_date, birth_time, birth_place)
        VALUES (?, ?, ?, ?)
    """, (name, birth_date, birth_time, birth_place))

    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return {
        "id": user_id,
        "name": name,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_place": birth_place
    }


def get_user_by_id(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row) 