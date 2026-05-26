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
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT 'Untitled',
            content TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
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


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


@app.get("/api/notes")
def list_notes(q: Optional[str] = None):
    conn = get_db()
    if q:
        notes = conn.execute(
            "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC",
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        notes = conn.execute(
            "SELECT * FROM notes ORDER BY updated_at DESC"
        ).fetchall()
    conn.close()
    return [dict(n) for n in notes]


@app.post("/api/notes")
def create_note(note: NoteCreate):
    ts = now_iso()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO notes (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (note.title, note.content, ts, ts)
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
    conn.execute(
        "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ?",
        (title, content, now_iso(), note_id)
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


# Serve SPA last so API routes take priority
app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
