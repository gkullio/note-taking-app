# Notes — Self-Hosted Note Taking App

A minimal, fast, self-hosted note-taking app.  
**Stack:** FastAPI · SQLite · Vanilla JS · Docker

---

## Quick Start

```bash
# Clone / copy this directory, then:
docker compose up -d --build
```

Open **http://localhost:8000** in your browser.

---

## Features

- Create, edit, delete notes with auto-save (800ms debounce)
- Full-text search across title and content
- Notes ordered by most recently updated
- Persistent SQLite database via Docker named volume
- Health check built in

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl/⌘ + N` | New note |
| `Ctrl/⌘ + F` | Focus search |
| `Escape` | Close dialogs |

---

## Management

```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f

# Rebuild after code changes
docker compose up -d --build

# Backup the database
docker run --rm -v notes-data:/data -v $(pwd):/backup alpine \
  cp /data/notes.db /backup/notes-backup.db

# Restore a backup
docker run --rm -v notes-data:/data -v $(pwd):/backup alpine \
  cp /backup/notes-backup.db /data/notes.db
```

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `/data/notes.db` | Path to the SQLite database |

To change the host port, edit `docker-compose.yml`:

```yaml
ports:
  - "3000:8000"   # expose on port 3000 instead
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/notes` | List all notes (supports `?q=search`) |
| `POST` | `/api/notes` | Create a note |
| `GET` | `/api/notes/{id}` | Get a single note |
| `PUT` | `/api/notes/{id}` | Update a note |
| `DELETE` | `/api/notes/{id}` | Delete a note |

---

## Putting it Behind a Reverse Proxy (Optional)

If you want HTTPS via NGINX or Caddy on the same host, point your reverse proxy at `http://localhost:8000`. Example Caddy snippet:

```
notes.yourdomain.com {
    reverse_proxy localhost:8000
}
```