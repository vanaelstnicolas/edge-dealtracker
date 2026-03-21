# Progress - DealTracker

Date: 2026-03-20

## Current state

- Backend now supports a Supabase-backed repository with automatic fallback to in-memory storage when Supabase env vars are missing.
- Frontend pages (`dashboard`, `pipeline`, `settings`) are connected to real backend APIs instead of local mock data.
- Microsoft Entra login is integrated through Supabase Auth in the frontend.
- Backend API routes for deals/dashboard/settings now enforce Supabase JWT bearer auth.
- Frontend API client now sends the Supabase access token in the `Authorization` header.
- Twilio webhook includes OpenAI NLU parsing with fallback to legacy text command parsing.
- A debug endpoint was added for NLU command parsing tests outside Twilio flow.

## Files added

- `backend/app/repositories/supabase.py`
- `backend/app/api/deps/auth.py`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/supabase.ts`
- `frontend/src/pages/LoginPage.tsx`
- `progress.md`

## Files modified

- `backend/app/repositories/in_memory.py`
- `backend/app/api/routes/twilio.py`
- `backend/app/api/routes/deals.py`
- `backend/app/api/routes/dashboard.py`
- `backend/app/api/routes/settings.py`
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

- `GET /api/deals` -> consumed by Dashboard + Pipeline, now requires bearer token and is scoped to authenticated owner
- `GET /api/settings/users` and `PUT /api/settings/users/{user_id}` -> consumed by Settings, now require bearer token
- `GET /api/dashboard/kpis` -> now requires bearer token
- `POST /api/webhooks/twilio` -> now uses OpenAI NLU conversion to internal command format when possible
- `POST /api/webhooks/twilio/debug/parse` -> local debug endpoint (disabled when `ENVIRONMENT=prod`)

## Validation completed

- Manual API auth checks done in PowerShell:
  - `GET /api/health` works without token.
  - `GET /api/deals` without token returns `401 Missing bearer token`.
  - `GET /api/deals` with bearer token succeeds (`200`), currently returns an empty list for the authenticated user.

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

1. Persist authenticated user profile into `users` (upsert on login) to align user IDs and deal ownership.
2. Add a small backend test suite for repository + protected route auth behavior.
3. Remove or restrict debug endpoint outside dev/staging environments.

## Update - 2026-03-21

### Completed

- Auth flow now upserts authenticated user profile into `users` on bearer-token validation (`id`, `email`, `full_name`) for both Supabase and in-memory stores.
- `UserMapping.whatsapp_number` is now nullable to support newly synced users before WhatsApp number assignment.
- Frontend API mapping now safely handles nullable `whatsapp_number` values by normalizing `null` to an empty string.
- Twilio debug parse endpoint is now restricted to `dev` and `staging` only.
- Backend test suite added with pytest covering:
  - protected route auth behavior (`/api/deals`)
  - user profile sync on authenticated requests
  - in-memory repository user upsert behavior
  - debug endpoint environment guard

### New next steps

1. Add user scoping to dashboard KPIs so they reflect only authenticated owner data.
2. Add Supabase integration tests (or mocked HTTP contract tests) for user upsert conflict scenarios.
3. Add stricter auth on settings update to ensure only authorized roles can update other users.

## Update - 2026-03-21 (KPI scoping)

### Completed

- `GET /api/dashboard/kpis` now scopes KPIs to the authenticated user (`owner_id = current_user.id`).
- Repository KPI implementations now support owner scoping in both stores:
  - `InMemoryStore.dashboard_kpis(owner_id=...)`
  - `SupabaseStore.dashboard_kpis(owner_id=...)`
- Added tests for KPI scoping behavior:
  - route-level owner forwarding
  - repository-level owner filtering

### Remaining next steps

1. Add Supabase integration tests (or mocked HTTP contract tests) for user upsert conflict scenarios.
2. Add stricter auth on settings update to ensure only authorized roles can update other users.

## Update - 2026-03-21 (settings authz + supabase tests)

### Completed

- Added mocked Supabase contract tests for `upsert_user_profile`:
  - successful merge/upsert response
  - conflict path raising `httpx.HTTPStatusError` (email unique violation)
- Added stricter authorization on `PUT /api/settings/users/{user_id}`:
  - user can update own mapping
  - admin (`app_metadata.role == "admin"` or `app_metadata.roles` contains `admin`) can update other users
  - non-admin cross-user update now returns `403 Forbidden owner scope`
- Added route-level tests for settings authorization behavior.

### New next steps

1. Add explicit role management policy/documentation for who should have `admin` in Supabase metadata.
2. Consider applying the same admin/self authorization pattern to `GET /api/settings/users` if full user list should be restricted.
3. Add frontend UX feedback for `403` on settings update (clear permission error message).

## Update - 2026-03-21 (settings listing + UX errors)

### Completed

- `GET /api/settings/users` is now role-aware:
  - admin gets full user list
  - non-admin gets only own user mapping
- Added backend authorization tests for settings list scope:
  - non-admin self-only listing
  - admin full listing
- Improved frontend settings error UX:
  - `403 Forbidden owner scope` is now displayed as a clear permission message in French.

### Remaining next steps

1. Add explicit role management policy/documentation for `admin` assignment in Supabase metadata.
2. Optionally enforce the same admin/self pattern on any future settings endpoints to keep authorization consistent.
3. Add CI workflow to run backend tests + frontend build on every push/PR.

## Update - 2026-03-21 (CI + role policy)

### Completed

- Added GitHub Actions CI workflow (`.github/workflows/ci.yml`) with:
  - backend job: install requirements + run `pytest`
  - frontend job: `npm ci` + `npm run build`
- Added explicit Supabase role governance policy (`docs/roles-policy.md`) covering:
  - `user` vs `admin` permissions
  - assignment/revocation process
  - operational security rules
- Updated root README to reflect current architecture and point to CI/policy docs.

### Remaining next steps

1. Wire branch protection rules so PR merge requires CI checks to pass.
2. Add role-change operational checklist in your internal runbook/tooling (ticket + audit trail).
3. Add optional smoke/e2e checks in CI for key business paths (login, deals fetch, settings update).

## Update - 2026-03-21 (Sprint 3/4 finalization package)

### Completed

- CI strengthened with backend smoke job in `.github/workflows/ci.yml`:
  - starts API
  - checks `/api/health` returns `200`
  - checks `/api/deals` without token returns `401`
- Branch protection helper scripts updated to require all checks:
  - `Backend Tests`
  - `Backend Smoke`
  - `Frontend Build`
- Added verification scripts for branch protection API state.
- Added authorization matrix documentation (`docs/authz-matrix.md`).
- Added release checklist documentation (`docs/release-checklist.md`).

### Remaining external action

1. Apply branch protection on the remote GitHub repository (cannot be executed locally without remote + GitHub CLI/token context in this environment).
