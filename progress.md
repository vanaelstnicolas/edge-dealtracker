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

## Update - 2026-03-21 (business smoke/e2e CI)

### Completed

- Added a minimal business smoke/e2e backend test (`backend/tests/test_business_smoke_paths.py`) covering key paths in one flow:
  - auth gate on protected endpoint (`/api/deals` returns `401` without bearer token)
  - authenticated deals listing (`GET /api/deals`)
  - authenticated settings listing scope (`GET /api/settings/users`)
  - authenticated settings update (`PUT /api/settings/users/{user_id}`)
- Added a dedicated CI job `Business E2E Smoke` in `.github/workflows/ci.yml` to run this journey test on every push/PR.

### Remaining next steps

1. Add a frontend browser-level smoke (Playwright) for the login screen rendering and auth redirect trigger.
2. Decide whether branch protection should require `Business E2E Smoke` in addition to existing checks.

## Update - 2026-03-21 (Excel pipeline import)

### Completed

- Added backend Excel import endpoint `POST /api/deals/import/excel` in `backend/app/api/routes/deals.py`.
- Import supports `.xlsx` files and maps business columns to deals:
  - `Cibles commerciales` -> `company`
  - `Avancement` + `Autres actions/questions-commentaires` -> `description`
  - `Actions commerciales` -> `action`
- Import infers status from row text (`lost` for closure/negative markers, `won` for signature/win markers, else `active`).
- Imported deals are always owner-scoped to authenticated user (`owner_id = current_user.id`) and get default deadline as current date.
- Added frontend upload action in Pipeline page (`Importer Excel`) and automatic list refresh after import.
- Added backend tests in `backend/tests/test_deals_excel_import.py` for happy path and invalid file type.

### Notes

- Current import handles first-sheet bulk onboarding and intentionally prioritizes robustness over strict row rejection for partially filled rows.

## Update - 2026-03-21 (pipeline inline edit)

### Completed

- Added inline edition flow in Pipeline UI (`frontend/src/pages/PipelinePage.tsx`) to edit existing dossiers.
- Editable fields now include:
  - `description`
  - `action`
  - `deadline`
  - `status`
  - `owner`
- Added frontend API update support in `frontend/src/lib/api.ts` via `PATCH /api/deals/{deal_id}`.
- Extended backend deal update schema with optional `owner_id` (`backend/app/schemas/deal.py`).
- Added authorization guard in `backend/app/api/routes/deals.py`:
  - non-admin cannot reassign owner to another user
  - admin can reassign owner
- Added backend authz tests for owner reassignment:
  - `backend/tests/test_deals_update_authz.py`

## Update - 2026-03-21 (WhatsApp real test trigger)

### Completed

- Added secured endpoint `POST /api/settings/users/{user_id}/whatsapp/test` to send a real Twilio WhatsApp test message.
- Authorization on test send follows existing policy:
  - user can trigger test for self
  - admin can trigger test for other users
- Added Settings UI action `Tester WhatsApp` per user row (`frontend/src/pages/SettingsPage.tsx`).
- Added API client helper `sendWhatsappTest` (`frontend/src/lib/api.ts`).
- Added backend tests in `backend/tests/test_settings_whatsapp_test.py`.

## Update - 2026-03-21 (Twilio replies + CI stabilization + merge)

### Completed

- Updated Twilio inbound webhook (`POST /api/webhooks/twilio`) to return TwiML XML responses so WhatsApp users receive immediate reply messages.
- Added webhook reply tests (`backend/tests/test_twilio_webhook_reply.py`) for text command and media acknowledgement paths.
- Improved Twilio outbound error visibility by surfacing Twilio API code/message details in backend error responses.
- Fixed CI reliability issues:
  - set workflow push branch to `main` (instead of `master`)
  - added `PYTHONPATH=.` for backend test jobs in GitHub Actions
  - fixed frontend type errors by adding missing `ownerId` values in `frontend/src/lib/mock-data.ts`
- Validated end-to-end WhatsApp flow in real environment:
  - outbound test message from Settings received on device
  - inbound WhatsApp command created a deal in Pipeline
  - webhook now replies to WhatsApp sender with command result
- Feature branch PR merged into `main` after all required checks passed.

### Suggested next session

1. Add owner dropdown by first name for assignment flows (derive display from `prenom.nom@edge-consulting.biz`).
2. Reduce perceived frontend latency between pages via request caching/prefetching.
3. Add a lightweight Playwright smoke test for login + pipeline navigation.

## Update - 2026-03-22 (owner dropdown by first name)

### Completed

- Updated Pipeline owner assignment dropdown to display users by first name.
- First name is derived from email local-part (`prenom.nom@...` -> `Prenom`) with fallback to `full_name`.
- Added duplicate first-name handling by displaying `Prenom (Full Name)` when needed.

### Next step

1. Improve frontend page transition speed via data caching/prefetch.

## Update - 2026-03-22 (frontend perceived performance)

### Completed

- Added lightweight client-side GET caching in `frontend/src/lib/api.ts` (30s TTL).
- Added in-flight request deduplication so repeated navigation does not trigger duplicate concurrent calls.
- Added cache invalidation hooks after mutations/imports:
  - `updateUserWhatsapp`
  - `updateDeal`
  - `importDealsFromExcel`
- Added app-level prefetch on authenticated session (`prefetchCoreData` in `frontend/src/App.tsx`) to warm deals/users data before page navigation.
- Updated Pipeline owner display to show first-name labels consistently in table view (not only in edit dropdown).

### Next step

1. Add Playwright smoke test for login + navigation + pipeline render.

## Update - 2026-03-22 (owner display normalization)

### Completed

- Normalized owner display labels to first-name format across UI contexts where `prenom.nom` appeared.
- `fetchDeals` now maps owner display using first-name derivation from user email/local-part.
- Settings user column now displays first-name format as well.

## Update - 2026-03-22 (WhatsApp NLU + vocal + weekly summaries)

### Completed

- Enhanced WhatsApp NLU intent extraction to support unstructured natural messages (create/update/close/summary) with sensible defaults.
- Added audio message handling path in Twilio webhook:
  - fetches media from Twilio
  - attempts OpenAI transcription
  - routes transcription through the same command parser
- Added owner action summary service and API routes:
  - `GET /api/summary/me` (fetch current user to-do summary)
  - `POST /api/summary/me/send` (send summary to user channels)
- Added Dashboard controls to:
  - display personal to-do summary in-app
  - trigger summary send on WhatsApp + email
- Added weekly scheduler job scaffolding for Monday 09:00 owner summaries (timezone-configurable).
- Added backend notification utilities for Twilio WhatsApp and SMTP email.
- Added tests for new summary routes and Twilio webhook reply scenarios.

### Configuration notes

- New env vars supported in backend config:
  - `OPENAI_TRANSCRIBE_MODEL`
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`
  - `WEEKLY_SUMMARY_SCHEDULER_ENABLED`, `WEEKLY_SUMMARY_TIMEZONE`, `WEEKLY_SUMMARY_DAY_OF_WEEK`, `WEEKLY_SUMMARY_HOUR`

## Update - 2026-03-22 (weekly summary ops controls)

### Completed

- Added admin API controls to operate weekly sends safely:
  - `POST /api/summary/weekly/trigger` (manual immediate run)
  - `GET /api/summary/weekly/status` (configured schedule visibility)
- Added test coverage for admin authorization and manual trigger execution (`backend/tests/test_summary_routes.py`).

## Backlog - next priorities

1. Configure production SMTP sender account (technical mailbox)
   - create dedicated sender (e.g. `noreply@edge-consulting.biz`)
   - configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`
   - validate Monday 09:00 scheduled summaries over email in staging/production

2. Frontend UX/UI refinements
   - replace technical channel statuses with polished badges/toasts in Dashboard summary card
   - improve spacing/typography and success/error hierarchy for summary actions
   - add consistent first-name display and humanized status labels across all pages
