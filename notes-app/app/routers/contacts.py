from fastapi import APIRouter, HTTPException
from database import get_db
from models import ContactUpdate

router = APIRouter(prefix="/api/contacts")


@router.put("/{contact_id}")
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


@router.delete("/{contact_id}")
def delete_contact(contact_id: int):
    conn = get_db()
    if not conn.execute("SELECT id FROM contacts WHERE id = ?", (contact_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Contact not found")
    conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()
    return {"ok": True}
