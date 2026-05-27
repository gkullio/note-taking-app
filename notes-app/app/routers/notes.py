from fastapi import APIRouter, HTTPException
from typing import Optional
from database import get_db, now_iso
from models import NoteCreate, NoteUpdate

router = APIRouter(prefix="/api/notes")


@router.get("")
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


@router.post("")
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


@router.get("/{note_id}")
def get_note(note_id: int):
    conn = get_db()
    note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(note)


@router.put("/{note_id}")
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


@router.delete("/{note_id}")
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
