from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db
from routers import notes, companies, contacts

app = FastAPI(title="Notes API")

init_db()

app.include_router(notes.router)
app.include_router(companies.router)
app.include_router(contacts.router)

app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
