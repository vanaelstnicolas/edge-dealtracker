# DealTracker MVP

Initial implementation for Sprint 0/1:

- React + Tailwind frontend with 3 pages (`/dashboard`, `/pipeline`, `/settings`)
- FastAPI backend with foundational API routes
- Supabase SQL migration for initial schema (`users`, `deals`)

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Next steps

1. Plug backend repository layer to Supabase
2. Add Supabase Auth (email/password)
3. Secure Twilio webhook signature validation
4. Connect frontend pages to backend API
