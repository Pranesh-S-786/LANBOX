"""
Database management module for LANBOX Server.
Handles user credentials, message history, announcements, file metadata, and server metrics.
"""
import sqlite3
import hashlib
import secrets
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path: str = "lanbox.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_username TEXT NOT NULL,
                    recipient_username TEXT,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    priority TEXT DEFAULT 'normal',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shared_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT UNIQUE NOT NULL,
                    sender TEXT NOT NULL,
                    recipient TEXT,
                    filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

    def register_user(self, username: str, password: str, role: str = "user") -> tuple[bool, str]:
        username = username.strip()
        if not username or not password:
            return False, "Username and password cannot be empty."
        if len(username) < 3:
            return False, "Username must be at least 3 characters."
        if len(password) < 4:
            return False, "Password must be at least 4 characters."

        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt, role, last_login) VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, salt, role, now_str)
            )
            conn.commit()
            return True, "User registered successfully."
        except sqlite3.IntegrityError:
            return False, f"Username '{username}' is already taken."
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
        finally:
            conn.close()

    def authenticate_user(self, username: str, password: str) -> tuple[bool, str]:
        username = username.strip()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                return False, "User not found. Please register."

            stored_hash = row["password_hash"]
            salt = row["salt"]
            computed_hash = self._hash_password(password, salt)

            if computed_hash == stored_hash:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("UPDATE users SET last_login = ? WHERE username = ?", (now_str, username))
                conn.commit()
                return True, "Login successful."
            else:
                return False, "Incorrect password."
        except Exception as e:
            return False, f"Authentication error: {str(e)}"
        finally:
            conn.close()

    def save_message(self, sender: str, recipient: str | None, content: str) -> dict:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (sender_username, recipient_username, content, timestamp) VALUES (?, ?, ?, ?)",
                (sender, recipient, content, timestamp)
            )
            conn.commit()
            msg_id = cursor.lastrowid
            return {
                "id": msg_id,
                "sender": sender,
                "recipient": recipient,
                "content": content,
                "timestamp": timestamp
            }
        finally:
            conn.close()

    def get_direct_history(self, user1: str, user2: str, limit: int = 50) -> list[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sender_username, recipient_username, content, timestamp
                FROM messages
                WHERE (sender_username = ? AND recipient_username = ?)
                   OR (sender_username = ? AND recipient_username = ?)
                ORDER BY id ASC
                LIMIT ?
            ''', (user1, user2, user2, user1, limit))
            rows = cursor.fetchall()
            return [
                {
                    "sender": r["sender_username"],
                    "recipient": r["recipient_username"],
                    "content": r["content"],
                    "timestamp": r["timestamp"]
                }
                for r in rows
            ]
        finally:
            conn.close()

    def get_broadcast_history(self, limit: int = 50) -> list[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sender_username, recipient_username, content, timestamp
                FROM messages
                WHERE recipient_username IS NULL OR recipient_username = ''
                ORDER BY id ASC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            return [
                {
                    "sender": r["sender_username"],
                    "recipient": None,
                    "content": r["content"],
                    "timestamp": r["timestamp"]
                }
                for r in rows
            ]
        finally:
            conn.close()

    def create_announcement(self, author: str, title: str, content: str, priority: str = "normal") -> dict:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO announcements (author, title, content, priority, timestamp) VALUES (?, ?, ?, ?, ?)",
                (author, title, content, priority, timestamp)
            )
            conn.commit()
            ann_id = cursor.lastrowid
            return {
                "id": ann_id,
                "author": author,
                "title": title,
                "content": content,
                "priority": priority,
                "timestamp": timestamp
            }
        finally:
            conn.close()

    def get_announcements(self, limit: int = 30) -> list[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, author, title, content, priority, timestamp
                FROM announcements
                ORDER BY id DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "author": r["author"],
                    "title": r["title"],
                    "content": r["content"],
                    "priority": r["priority"],
                    "timestamp": r["timestamp"]
                }
                for r in rows
            ]
        finally:
            conn.close()

    def record_shared_file(self, file_id: str, sender: str, recipient: str | None, filename: str, file_size: int):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO shared_files (file_id, sender, recipient, filename, file_size, status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (file_id, sender, recipient, filename, file_size, "completed", timestamp)
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_registered_users(self) -> list[str]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users ORDER BY username ASC")
            rows = cursor.fetchall()
            return [r["username"] for r in rows]
        finally:
            conn.close()
