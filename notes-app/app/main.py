from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(title="Notes API")

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
    # Migrate existing databases that are missing the new columns
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
    conn.commit()
    conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


init_db()


class NoteCreate(BaseModel):
    title: str = "Untitled"
    content: str = ""
    account_manager: str = ""
    company_name: str = ""
    date_last_contacted: str = ""
    salesforce_url: str = ""


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    account_manager: Optional[str] = None
    company_name: Optional[str] = None
    date_last_contacted: Optional[str] = None
    salesforce_url: Optional[str] = None


class AccountNotesUpsert(BaseModel):
    content: str = ""


class ContactCreate(BaseModel):
    name: str = ""
    email: str = ""
    team: str = ""
    phone: str = ""


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    team: Optional[str] = None
    phone: Optional[str] = None


@app.get("/api/companies")
def list_companies(q: Optional[str] = None):
    conn = get_db()
    if q:
        rows = conn.execute("""
            SELECT company_name, COUNT(*) as note_count, MAX(updated_at) as last_updated
            FROM notes
            WHERE company_name != '' AND company_name LIKE ?
            GROUP BY company_name
            ORDER BY last_updated DESC
        """, (f"%{q}%",)).fetchall()
    else:
        rows = conn.execute("""
            SELECT company_name, COUNT(*) as note_count, MAX(updated_at) as last_updated
            FROM notes
            WHERE company_name != ''
            GROUP BY company_name
            ORDER BY last_updated DESC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/notes")
def list_notes(q: Optional[str] = None, company: Optional[str] = None):
    conn = get_db()
    conditions = []
    params = []
    if company is not None:
        conditions.append("company_name = ?")
        params.append(company)
    if q:
        conditions.append("(title LIKE ? OR content LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    notes = conn.execute(
        f"SELECT * FROM notes {where} ORDER BY updated_at DESC", params
    ).fetchall()
    conn.close()
    return [dict(n) for n in notes]


@app.post("/api/notes")
def create_note(note: NoteCreate):
    ts = now_iso()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO notes (title, content, account_manager, company_name, date_last_contacted, salesforce_url, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (note.title, note.content, note.account_manager, note.company_name, note.date_last_contacted, note.salesforce_url, ts, ts)
    )
    conn.commit()
    new = conn.execute("SELECT * FROM notes WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(new)


@app.get("/api/notes/{note_id}")
def get_note(note_id: int):
    conn = get_db()
    note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(note)


@app.put("/api/notes/{note_id}")
def update_note(note_id: int, note: NoteUpdate):
    conn = get_db()
    existing = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
    title = note.title if note.title is not None else existing["title"]
    content = note.content if note.content is not None else existing["content"]
    account_manager = note.account_manager if note.account_manager is not None else existing["account_manager"]
    company_name = note.company_name if note.company_name is not None else existing["company_name"]
    date_last_contacted = note.date_last_contacted if note.date_last_contacted is not None else existing["date_last_contacted"]
    salesforce_url = note.salesforce_url if note.salesforce_url is not None else existing["salesforce_url"]
    conn.execute(
        "UPDATE notes SET title = ?, content = ?, account_manager = ?, company_name = ?, date_last_contacted = ?, salesforce_url = ?, updated_at = ? WHERE id = ?",
        (title, content, account_manager, company_name, date_last_contacted, salesforce_url, now_iso(), note_id)
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int):
    conn = get_db()
    existing = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/companies/{company_name}/account-notes")
def get_account_notes(company_name: str):
    conn = get_db()
    row = conn.execute(
        "SELECT content FROM account_notes WHERE company_name = ?", (company_name,)
    ).fetchone()
    conn.close()
    return {"content": row["content"] if row else ""}


@app.put("/api/companies/{company_name}/account-notes")
def upsert_account_notes(company_name: str, data: AccountNotesUpsert):
    conn = get_db()
    conn.execute("""
        INSERT INTO account_notes (company_name, content) VALUES (?, ?)
        ON CONFLICT(company_name) DO UPDATE SET content = excluded.content
    """, (company_name, data.content))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/companies/{company_name}/contacts")
def list_company_contacts(company_name: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM contacts WHERE company_name = ? ORDER BY id ASC", (company_name,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/companies/{company_name}/contacts")
def create_company_contact(company_name: str, contact: ContactCreate):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO contacts (company_name, name, email, team, phone) VALUES (?, ?, ?, ?, ?)",
        (company_name, contact.name, contact.email, contact.team, contact.phone)
    )
    conn.commit()
    new = conn.execute("SELECT * FROM contacts WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(new)


@app.put("/api/contacts/{contact_id}")
def update_contact(contact_id: int, contact: ContactUpdate):
    conn = get_db()
    existing = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Contact not found")
    name  = contact.name  if contact.name  is not None else existing["name"]
    email = contact.email if contact.email is not None else existing["email"]
    team  = contact.team  if contact.team  is not None else existing["team"]
    phone = contact.phone if contact.phone is not None else existing["phone"]
    conn.execute(
        "UPDATE contacts SET name = ?, email = ?, team = ?, phone = ? WHERE id = ?",
        (name, email, team, phone, contact_id)
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.delete("/api/contacts/{contact_id}")
def delete_contact(contact_id: int):
    conn = get_db()
    if not conn.execute("SELECT id FROM contacts WHERE id = ?", (contact_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Contact not found")
    conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# Serve SPA last so API routes take priority
app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
