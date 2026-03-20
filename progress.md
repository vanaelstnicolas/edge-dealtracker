# Progress - DealTracker

Date: 2026-03-20

## Current state

- Backend now supports a Supabase-backed repository with automatic fallback to in-memory storage when Supabase env vars are missing.
- Frontend pages (`dashboard`, `pipeline`, `settings`) are connected to real backend APIs instead of local mock data.
- Microsoft Entra login is integrated through Supabase Auth in the frontend.
- Twilio webhook includes OpenAI NLU parsing with fallback to legacy text command parsing.
- A debug endpoint was added for NLU command parsing tests outside Twilio flow.

## Files added

- `backend/app/repositories/supabase.py`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/supabase.ts`
- `frontend/src/pages/LoginPage.tsx`
- `progress.md`

## Files modified

- `backend/app/repositories/in_memory.py`
- `backend/app/api/routes/twilio.py`
- `frontend/src/App.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/PipelinePage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/package.json`
- `frontend/package-lock.json`

## Configuration required (local)

### Backend (`backend/.env.local`)

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (preferred) or `SUPABASE_ANON_KEY`
- `TWILIO_AUTH_TOKEN`, `TWILIO_ACCOUNT_SID`, `TWILIO_WHATSAPP_NUMBER`
- `MISTRAL_API_KEY`
- `OPENAI_API_KEY`
- Optional: `OPENAI_NLU_MODEL` (defaults to `gpt-5-mini`)

### Frontend (`frontend/.env.local`)

- `VITE_API_BASE_URL=http://127.0.0.1:8000/api`
- `VITE_SUPABASE_URL=https://<project-ref>.supabase.co`
- `VITE_SUPABASE_ANON_KEY=<anon-key>`

## Microsoft Entra + Supabase notes

- Supabase Azure provider is configured and functional after fixing `Azure Tenant URL`.
- Correct tenant URL format is:
  - `https://login.microsoftonline.com/<TENANT_ID>`
  - Do not append `/v2.0` (Supabase appends OAuth path itself).
- Frontend login uses `prompt=select_account`.
- Sidebar includes a `Se deconnecter` action.

## API/feature checkpoints

- `GET /api/deals` -> consumed by Dashboard + Pipeline
- `GET /api/settings/users` and `PUT /api/settings/users/{user_id}` -> consumed by Settings
- `POST /api/webhooks/twilio` -> now uses OpenAI NLU conversion to internal command format when possible
- `POST /api/webhooks/twilio/debug/parse` -> local debug endpoint (disabled when `ENVIRONMENT=prod`)

## How to run locally

### Backend

1. `cd backend`
2. `python -m venv .venv`
3. `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `uvicorn app.main:app --reload`

### Frontend

1. `cd frontend`
2. `npm install`
3. `npm run dev`

## Suggested next steps

1. Enforce Supabase JWT verification on backend API routes.
2. Persist authenticated user profile into `users` (upsert on login).
3. Add a small backend test suite for repository + Twilio command paths.
4. Remove or restrict debug endpoint outside dev/staging environments.
