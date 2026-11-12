import sqlite3
import os
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")
MAX_MESSAGES = 50  # Bir foydalanuvchi konteksti uchun maksimal xotira

def init_db():
    """Barcha jadvallarni yaratish va yangilash."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Shaxsiy suhbat konteksti (xotira)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON chat_history (user_id)")
    
    # 2. Foydalanuvchilar jadvali (Admin uchun)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            msg_count INTEGER DEFAULT 1
        )
    """)
    
    # 3. Umumiy savol-javoblar jurnali (Admin monitoringi uchun)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT,
            msg_type TEXT,
            user_text TEXT,
            bot_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user_id ON chat_logs (user_id)")
    
    conn.commit()
    conn.close()

# --- Xotira funksiyalari ---

def add_message(user_id: int, role: str, content: str):
    """Foydalanuvchi xotirasiga yozish (50 ta xabar chegarasi)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    cursor.execute("SELECT id FROM chat_history WHERE user_id = ? ORDER BY id ASC", (user_id,))
    rows = cursor.fetchall()
    if len(rows) > MAX_MESSAGES:
        excess = len(rows) - MAX_MESSAGES
        ids_to_delete = [row[0] for row in rows[:excess]]
        cursor.execute(
            f"DELETE FROM chat_history WHERE id IN ({','.join(['?']*len(ids_to_delete))})",
            ids_to_delete
        )
    conn.commit()
    conn.close()

def get_history(user_id: int) -> List[Dict[str, str]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY id ASC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def get_memory_stats(user_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    percent = int((count / MAX_MESSAGES) * 100)
    return {
        "count": count,
        "max": MAX_MESSAGES,
        "percent": percent,
        "is_full": count >= MAX_MESSAGES
    }

def clear_user_memory(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- Admin panel funksiyalari ---

def upsert_user(user_id: int, username: Optional[str], full_name: str):
    """Foydalanuvchini bazaga qo'shish yoki oxirgi faolligini yangilash."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, full_name, last_seen, msg_count)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            full_name=excluded.full_name,
            last_seen=CURRENT_TIMESTAMP,
            msg_count=users.msg_count + 1
    """, (user_id, username, full_name))
    conn.commit()
    conn.close()

def log_interaction(user_id: int, full_name: str, msg_type: str, user_text: str, bot_response: str):
    """Admin monitoringi uchun savol-javobni qayd qilish."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_logs (user_id, full_name, msg_type, user_text, bot_response)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, full_name, msg_type, user_text, bot_response))
    conn.commit()
    conn.close()

def get_admin_stats() -> dict:
    """Admin uchun umumiy statistika."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM chat_logs")
    total_logs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(last_seen) = DATE('now')")
    today_active = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_users": total_users,
        "total_logs": total_logs,
        "today_active": today_active
    }

def get_recent_users(limit: int = 10) -> list:
    """So'nggi faol foydalanuvchilar."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, username, full_name, last_seen, msg_count
        FROM users ORDER BY last_seen DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "user_id": r[0],
            "username": r[1],
            "full_name": r[2],
            "last_seen": r[3],
            "msg_count": r[4]
        }
        for r in rows
    ]

def get_recent_chat_logs(limit: int = 5, offset: int = 0) -> list:
    """Admin uchun so'nggi savol-javoblar lentasi."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, full_name, msg_type, user_text, bot_response, created_at
        FROM chat_logs ORDER BY id DESC LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "full_name": r[2],
            "msg_type": r[3],
            "user_text": r[4],
            "bot_response": r[5],
            "created_at": r[6]
        }
        for r in rows
    ]

def get_all_user_ids() -> List[int]:
    """Barcha foydalanuvchilar ID ro'yxati (xabar tarqatish uchun)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    return ids
