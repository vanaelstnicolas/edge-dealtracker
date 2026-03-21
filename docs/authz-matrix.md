# Authorization Matrix

This matrix captures expected authorization behavior for currently exposed API routes.

## Roles

- `user`: default authenticated role
- `admin`: privileged role from Supabase `app_metadata`

## Route Matrix

| Route | Method | user | admin | Notes |
|---|---|---|---|---|
| `/api/health` | GET | allow | allow | public route |
| `/api/deals` | GET | allow (own scope) | allow (own scope) | owner scope enforced from JWT id |
| `/api/deals` | POST | allow (owner must match JWT id) | allow (owner must match JWT id) | cross-owner creation blocked |
| `/api/deals/{deal_id}` | PATCH | allow (own deal only) | allow (own deal only) | currently no admin override |
| `/api/dashboard/kpis` | GET | allow (own scope) | allow (own scope) | KPIs scoped by authenticated owner |
| `/api/settings/users` | GET | allow (self only) | allow (all users) | role-aware listing |
| `/api/settings/users/{user_id}` | PUT | allow (self only) | allow (all users) | role-aware update |
| `/api/webhooks/twilio` | POST | n/a | n/a | Twilio signature + WhatsApp lookup |
| `/api/webhooks/twilio/debug/parse` | POST | dev/staging only | dev/staging only | disabled outside dev/staging |

## Notes

- Auth is enforced through Supabase bearer JWT validation (`get_current_user`).
- `admin` is resolved via `app_metadata.role == "admin"` or `app_metadata.roles` containing `admin`.
- New routes should explicitly document user/admin behavior in this file.
