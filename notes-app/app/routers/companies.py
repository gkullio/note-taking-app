from fastapi import APIRouter
from typing import Optional
from database import get_db
from models import AccountNotesUpsert, ContactCreate

router = APIRouter(prefix="/api/companies")


@router.get("")
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


@router.get("/{company_name}/account-notes")
def get_account_notes(company_name: str):
    conn = get_db()
    row = conn.execute(
        "SELECT content FROM account_notes WHERE company_name = ?", (company_name,)
    ).fetchone()
    conn.close()
    return {"content": row["content"] if row else ""}


@router.put("/{company_name}/account-notes")
def upsert_account_notes(company_name: str, data: AccountNotesUpsert):
    conn = get_db()
    conn.execute("""
        INSERT INTO account_notes (company_name, content) VALUES (?, ?)
        ON CONFLICT(company_name) DO UPDATE SET content = excluded.content
    """, (company_name, data.content))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/{company_name}/contacts")
def list_company_contacts(company_name: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM contacts WHERE company_name = ? ORDER BY id ASC", (company_name,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/{company_name}/contacts")
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
