# Dealership Creative Automation Tool

Web app to bulk-generate dealership social creatives (background + footer panel + optional logo) in Instagram sizes. Headline and body text are shortened **in the app** (word-aware truncation) to fit the layout—no external APIs.

## Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy (SQLite by default), Pillow, JWT auth  
- **Frontend:** React 18 + Vite + React Router  

## Default admin (seed)

| Field    | Value              |
|----------|--------------------|
| Email    | `admin@example.com` |
| Password | `admin123`         |

## Setup

### Backend

```bash
cd backend
cp .env.example .env   # optional; edit secrets
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On first startup the API creates `backend/data/`, SQLite DB, tables, and seeds accounts, dealerships, and the admin user.

Environment variables are documented in **`backend/.env.example`**. With `backend/.env` present, values are loaded automatically (`python-dotenv`).

**AI hero (optional):** set `OPENAI_API_KEY` (and optionally `OPENAI_IMAGE_MODEL`, default `dall-e-3`). With “AI hero” enabled and no background upload, each output calls OpenAI **Images** for the hero, then the app composites text and logos in Pillow. An uploaded background still wins over AI.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 — the Vite dev server proxies `/api` to port 8000.

**UI:** After login you get a **sidebar dashboard** (Create Creatives, placeholders for History/Assets/etc.). **Sample images** for quick tests live under `frontend/public/samples/` (`vehicle-*.jpg`, logos) and are loadable from the Create screen via “Sample backgrounds” / “Use sample logo”.

### “attempt to write a readonly database” (SQLite)

The app must be able to write the SQLite file **and** its directory (for journals). From the project root:

```bash
chmod -R u+w backend/data
```

If the DB was created as another user (e.g. root), fix ownership or point `DATABASE_URL` at a folder you own.

### Database SQL file

`database.sql` contains SQLite-compatible DDL + seed rows (same accounts/dealerships + admin hash for `admin123`). You can initialize a DB manually:

```bash
mkdir -p backend/data
sqlite3 backend/data/app.db < database.sql
```

If the app has already created tables via SQLAlchemy, prefer a fresh `backend/data/app.db` before importing.

## API overview

- `POST /api/auth/login` — JSON `{ "email", "password" }` → JWT  
- `GET /api/accounts` — brands  
- `GET /api/accounts/{id}/dealerships`  
- `POST /api/uploads/background` — multipart `file` (JPG/PNG)  
- `POST /api/uploads/logo` — optional logo upload  
- `POST /api/jobs` — start bulk generation (JSON + prior upload IDs)  
- `GET /api/jobs/{id}` — status / progress  
- `GET /api/jobs/{id}/outputs` — list with `/api/jobs/{id}/files/{output_id}` URLs  
- `POST /api/jobs/{id}/download-zip` — body `{}` for all, or `{ "output_ids": [1,2,3] }`  

## Automation behavior

- **Smart background fit:** cover + center crop to each target size (no stretch).  
- **Panel:** uses `dealerships.panel_image_path` PNG when present; otherwise a synthetic footer with name, address, phone, website.  
- **Copy:** headline/body are trimmed in-process to fit wedge/banner areas (`copy_shorten.shorten_for_layout`).
- **Hero:** uploaded photo (cover crop), optional OpenAI Images-generated hero when `ai_generate_background` is true and no upload, or accent gradient.

## Production notes

- Set a strong `SECRET_KEY` environment variable.  
- Point `DATABASE_URL` to Postgres/MySQL if needed (adjust `connect_args` in `app/database.py`).  
- Serve generated files from object storage or a CDN for scale.
