from pydantic import BaseModel
from typing import Optional


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
