import sqlite3
import hashlib
import secrets

DB_NAME = "workouts.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON") 
    return conn

def hash_password(password, salt):
    return hashlib.sha256(str.encode(password + salt)).hexdigest()

def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT UNIQUE NOT NULL, 
            password TEXT NOT NULL, 
            salt TEXT NOT NULL, 
            is_admin INTEGER DEFAULT 0
        )
    """)
    # Merged table to support Day names AND calendar Dates
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER NOT NULL, 
            day TEXT, 
            name TEXT NOT NULL, 
            media_path TEXT,
            media_type TEXT,
            workout_date DATE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workout_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            workout_id INTEGER NOT NULL, 
            set_number INTEGER NOT NULL, 
            weight REAL, 
            reps INTEGER, 
            FOREIGN KEY (workout_id) REFERENCES workouts (id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def create_user(username, password):
    username = username.strip()
    if not username or not password: return False, "Fields cannot be empty."
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        is_admin = 1 if cur.fetchone()[0] == 0 else 0
        salt = secrets.token_hex(16) 
        hashed_p = hash_password(password, salt)
        cur.execute("INSERT INTO users (username, password, salt, is_admin) VALUES (?, ?, ?, ?)", 
                    (username, hashed_p, salt, is_admin))
        conn.commit()
        return True, "Account Created!"
    except sqlite3.IntegrityError: return False, "Username exists."
    finally: conn.close()

def login_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, password, salt, is_admin FROM users WHERE username = ?", (username.strip(),))
    user_data = cur.fetchone()
    conn.close()
    if user_data:
        uid, stored_hash, salt, is_admin = user_data
        if hash_password(password, salt) == stored_hash: return (uid, is_admin)
    return None

def add_workout(user_id, day, name, path, mtype, w_date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO workouts (user_id, day, name, media_path, media_type, workout_date) VALUES (?, ?, ?, ?, ?, ?)", 
                (user_id, day, name, path, mtype, w_date))
    conn.commit()
    conn.close()

def get_workouts(user_id, w_date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, media_path, media_type FROM workouts WHERE user_id = ? AND workout_date = ?", (user_id, w_date))
    return cur.fetchall()

def add_set(workout_id, set_num, weight, reps):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO workout_sets (workout_id, set_number, weight, reps) VALUES (?, ?, ?, ?)", (workout_id, set_num, weight, reps))
    conn.commit()
    conn.close()

def get_sets(workout_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT set_number, weight, reps FROM workout_sets WHERE workout_id = ? ORDER BY set_number", (workout_id,))
    return cur.fetchall()

def delete_workout(workout_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    conn.commit()
    conn.close()
