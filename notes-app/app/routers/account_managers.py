from fastapi import APIRouter, HTTPException
from database import get_db
from models import AccountManagerCreate

router = APIRouter(prefix="/api/account-managers")


@router.get("")
def list_account_managers():
    conn = get_db()
    rows = conn.execute("SELECT * FROM account_managers ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("")
def create_account_manager(data: AccountManagerCreate):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    conn = get_db()
    try:
        cur = conn.execute("INSERT INTO account_managers (name) VALUES (?)", (name,))
        conn.commit()
        new = conn.execute("SELECT * FROM account_managers WHERE id = ?", (cur.lastrowid,)).fetchone()
        conn.close()
        return dict(new)
    except Exception:
        conn.close()
        raise HTTPException(status_code=409, detail="Account manager already exists")
