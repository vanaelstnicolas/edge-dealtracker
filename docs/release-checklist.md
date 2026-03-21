# Release Checklist (MVP)

Use this checklist before merging a release PR to `master`.

## 1) Code Health

- [ ] Backend tests pass (`pytest`).
- [ ] Frontend build passes (`npm run build`).
- [ ] CI green on PR (`Backend Tests`, `Backend Smoke`, `Frontend Build`).

## 2) Security & Access

- [ ] Branch protection enabled on `master` with required checks.
- [ ] Role policy reviewed for any admin changes (`docs/roles-policy.md`).
- [ ] Settings authorization behavior validated (`user` self-only, `admin` full scope).

## 3) Configuration

- [ ] Backend environment variables set in target environment.
- [ ] Frontend environment variables set for target environment.
- [ ] Supabase Auth provider (Microsoft Entra) configuration verified.

## 4) Functional Smoke

- [ ] `GET /api/health` returns `200`.
- [ ] `GET /api/deals` without token returns `401`.
- [ ] Authenticated dashboard loads and shows user-scoped KPIs.
- [ ] Settings updates behave correctly for user/admin roles.

## 5) Rollback Readiness

- [ ] Previous stable commit/tag identified.
- [ ] Rollback command/process documented for current deployment target.
- [ ] Owner on-call and escalation contact confirmed.
