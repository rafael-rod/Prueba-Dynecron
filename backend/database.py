import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from config import DB_PATH

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initialize database tables"""
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                session_id TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                text TEXT NOT NULL,
                payload_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()

def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}

# Chat operations
def list_chats() -> List[Dict[str, Any]]:
    with db_connect() as conn:
        rows = conn.execute("SELECT id, title, created_at, session_id FROM chats ORDER BY id DESC").fetchall()
        return [row_to_dict(r) for r in rows]

def create_chat(title: str, session_id: str) -> Dict[str, Any]:
    created_at = datetime.utcnow().isoformat()
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO chats(title, created_at, session_id) VALUES(?,?,?)", (title, created_at, session_id))
        chat_id = cur.lastrowid
        conn.commit()
        return {"id": chat_id, "title": title, "created_at": created_at, "session_id": session_id}

def delete_chat(chat_id: int) -> Dict[str, str]:
    with db_connect() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))
        conn.commit()
    return {"status": "deleted"}

# Message operations
def list_messages(chat_id: int) -> List[Dict[str, Any]]:
    with db_connect() as conn:
        rows = conn.execute("SELECT id, chat_id, sender, text, payload_json, created_at FROM messages WHERE chat_id=? ORDER BY id ASC", (chat_id,)).fetchall()
        return [row_to_dict(r) for r in rows]

def add_message(chat_id: int, sender: str, text: str, payload_json: Dict[str, Any] = None) -> Dict[str, Any]:
    import json
    created_at = datetime.utcnow().isoformat()
    payload_str = json.dumps(payload_json) if payload_json is not None else None
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO messages(chat_id, sender, text, payload_json, created_at) VALUES(?,?,?,?,?)", (chat_id, sender, text, payload_str, created_at))
        msg_id = cur.lastrowid
        conn.commit()
        return {"id": msg_id, "chat_id": chat_id, "sender": sender, "text": text, "payload_json": payload_json, "created_at": created_at}
