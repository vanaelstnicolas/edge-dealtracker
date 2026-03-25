# DealTracker MVP

Current implementation status:

- React + Tailwind frontend (`/dashboard`, `/pipeline`, `/settings`, `/login`)
- FastAPI backend APIs with bearer auth enforcement on protected routes
- Supabase-backed repository with fallback to in-memory storage for local dev
- Microsoft Entra login integrated through Supabase Auth
- Supabase SQL migration for initial schema (`users`, `deals`)
- Twilio webhook with OpenAI NLU parsing + fallback command parser
- Weekly summary email provider supports Microsoft Graph (Entra OAuth2) with optional SMTP fallback

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

## CI

GitHub Actions workflow runs on push and pull requests:

- Backend: install deps + `pytest`
- Backend smoke: boot API + verify `health` and protected route behavior
- Business E2E smoke: run key auth/deals/settings journey test
- Frontend: `npm ci` + `npm run build`

Workflow file: `.github/workflows/ci.yml`

## Role policy

Supabase role assignment policy for `user`/`admin` is documented in:

- `docs/roles-policy.md`

## Security and release docs

- Authorization matrix: `docs/authz-matrix.md`
- Release checklist: `docs/release-checklist.md`
- SMTP setup: `docs/smtp-setup.md`

## Email smoke scripts

- PowerShell (status-only): `./smoke-summary-email.ps1 -Token <bearer-token>`
- PowerShell (send own summary): `./smoke-summary-email.ps1 -Token <bearer-token> -SendMySummary`
- Bash (status-only): `DEALTRACKER_BEARER_TOKEN=<token> ./smoke-summary-email.sh`
- Bash (send own summary): `DEALTRACKER_BEARER_TOKEN=<token> SEND_MY_SUMMARY=true ./smoke-summary-email.sh`
