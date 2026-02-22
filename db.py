import sqlite3
import hashlib
import secrets
import datetime

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
    
    # 1. Asosiy jadvallar
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, salt TEXT NOT NULL, 
        is_admin INTEGER DEFAULT 0, last_seen DATETIME, created_at DATE, profile_photo TEXT)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, 
        day TEXT, name TEXT NOT NULL, media_path TEXT, media_type TEXT, 
        workout_date DATE, FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS workout_sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, workout_id INTEGER NOT NULL, 
        set_number INTEGER NOT NULL, weight REAL, reps INTEGER, 
        FOREIGN KEY (workout_id) REFERENCES workouts (id) ON DELETE CASCADE)""")
    
    # SHAXSIY NOTElar uchun jadval
    cur.execute("""CREATE TABLE IF NOT EXISTS user_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER NOT NULL, 
        content TEXT NOT NULL, 
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE)""")

    cur.execute("CREATE TABLE IF NOT EXISTS broadcasts (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, created_at DATETIME)")
    cur.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL, receiver_id INTEGER NOT NULL, message TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, is_read INTEGER DEFAULT 0)")

    # 2. Migratsiyalar
    cur.execute("PRAGMA table_info(users)")
    u_cols = [info[1] for info in cur.fetchall()]
    for col in [("last_seen", "DATETIME"), ("created_at", "DATE"), ("profile_photo", "TEXT")]:
        if col[0] not in u_cols:
            try: cur.execute(f"ALTER TABLE users ADD COLUMN {col[0]} {col[1]}")
            except: pass

    conn.commit()
    conn.close()

# --- NOTE OPERATSIYALARI ---
def save_user_note(user_id, content):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO user_notes (user_id, content) VALUES (?, ?)", (user_id, content))
    conn.commit()
    conn.close()

def get_user_notes(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT content, created_at, id FROM user_notes WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    res = cur.fetchall()
    conn.close()
    return res

def delete_user_note(note_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

# --- AUTH & PROFILE ---
def login_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, password, salt, is_admin FROM users WHERE username = ?", (username.strip(),))
    user_data = cur.fetchone()
    conn.close()
    if user_data:
        uid, stored_hash, salt, is_admin = user_data
        if hash_password(password, salt) == stored_hash:
            update_last_seen(uid)
            return (uid, is_admin)
    return None

def create_user(username, password, is_admin=0):
    conn = get_connection()
    cur = conn.cursor()
    salt = secrets.token_hex(8)
    hashed_pw = hash_password(password, salt)
    try:
        cur.execute("INSERT INTO users (username, password, salt, is_admin, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?)", 
                    (username.strip(), hashed_pw, salt, is_admin, datetime.date.today(), datetime.datetime.now()))
        conn.commit()
        return True, "Muvaffaqiyatli ro'yxatdan o'tdingiz!"
    except: return False, "Username band!"
    finally: conn.close()

def get_user_info(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, profile_photo, created_at FROM users WHERE id = ?", (user_id,))
    res = cur.fetchone()
    conn.close()
    return res

def update_profile(user_id, new_username, photo_path=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        if photo_path:
            cur.execute("UPDATE users SET username = ?, profile_photo = ? WHERE id = ?", (new_username.strip(), photo_path, user_id))
        else:
            cur.execute("UPDATE users SET username = ? WHERE id = ?", (new_username.strip(), user_id))
        conn.commit()
        return True, "Profil yangilandi!"
    except sqlite3.IntegrityError: return False, "Username band!"
    finally: conn.close()

def delete_account(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_last_seen(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_seen = ? WHERE id = ?", (datetime.datetime.now(), user_id))
    conn.commit()
    conn.close()

# --- CHAT ---
def send_message(sid, rid, msg):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)", (sid, rid, msg))
    conn.commit()
    conn.close()

def get_chat_history(uid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT sender_id, message, timestamp FROM messages WHERE sender_id = ? OR receiver_id = ? ORDER BY timestamp ASC", (uid, uid))
    res = cur.fetchall()
    conn.close()
    return res

def get_unread_counts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT sender_id, COUNT(*) FROM messages WHERE receiver_id = 1 AND is_read = 0 GROUP BY sender_id")
    res = dict(cur.fetchall())
    conn.close()
    return res

def mark_as_read(target_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = 1", (target_id,))
    conn.commit()
    conn.close()

def get_users_with_messages():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT u.id, u.username FROM users u JOIN messages m ON u.id = m.sender_id WHERE u.id != 1")
    res = cur.fetchall()
    conn.close()
    return res

# --- WORKOUTS ---
def add_workout(user_id, day, name, path, mtype, w_date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO workouts (user_id, day, name, media_path, media_type, workout_date) VALUES (?, ?, ?, ?, ?, ?)", (user_id, day, name, path, mtype, w_date))
    conn.commit()
    conn.close()

def get_workouts(user_id, w_date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, media_path, media_type FROM workouts WHERE user_id = ? AND workout_date = ?", (user_id, w_date))
    res = cur.fetchall()
    conn.close()
    return res

def add_set(workout_id, sn, weight, reps):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO workout_sets (workout_id, set_number, weight, reps) VALUES (?, ?, ?, ?)", (workout_id, sn, weight, reps))
    conn.commit()
    conn.close()

def get_sets(workout_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT set_number, weight, reps FROM workout_sets WHERE workout_id = ? ORDER BY set_number ASC", (workout_id,))
    res = cur.fetchall()
    conn.close()
    return res

def delete_workout(wid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM workouts WHERE id = ?", (wid,))
    conn.commit()
    conn.close()

def set_broadcast(msg):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO broadcasts (message, created_at) VALUES (?, ?)", (msg, datetime.datetime.now()))
    conn.commit()
    conn.close()

def get_latest_broadcast():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT message FROM broadcasts ORDER BY id DESC LIMIT 1")
    res = cur.fetchone()
    conn.close()
    return res[0] if res else None

def get_admin_stats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE date(last_seen) = date('now')")
    active = cur.fetchone()[0]
    conn.close()
    return total, active
