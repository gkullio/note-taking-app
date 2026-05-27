import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.environ.get("DB_PATH", "/data/notes.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT 'Untitled',
            content TEXT NOT NULL DEFAULT '',
            account_manager TEXT NOT NULL DEFAULT '',
            company_name TEXT NOT NULL DEFAULT '',
            date_last_contacted TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    for col in ("account_manager", "company_name", "date_last_contacted", "salesforce_url"):
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE notes ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
    contact_cols = {row[1] for row in conn.execute("PRAGMA table_info(contacts)").fetchall()}
    if not contact_cols:
        conn.execute("""
            CREATE TABLE contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                team TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT ''
            )
        """)
    elif 'note_id' in contact_cols and 'company_name' not in contact_cols:
        conn.execute("""
            CREATE TABLE contacts_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                team TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            INSERT INTO contacts_new (id, company_name, name, email, team, phone)
            SELECT c.id, COALESCE(n.company_name, ''), c.name, c.email, c.team, c.phone
            FROM contacts c LEFT JOIN notes n ON c.note_id = n.id
        """)
        conn.execute("DROP TABLE contacts")
        conn.execute("ALTER TABLE contacts_new RENAME TO contacts")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS account_notes (
            company_name TEXT PRIMARY KEY,
            content TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS account_managers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    count = conn.execute("SELECT COUNT(*) FROM account_managers").fetchone()[0]
    if count == 0:
        conn.execute("INSERT INTO account_managers (name) VALUES (?)", ("Kirk MacCallum",))
    conn.commit()
    conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()
