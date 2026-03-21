# Role Management Policy (Supabase Auth)

## Goal

Define who can receive `admin` privileges in Supabase metadata and how these privileges are granted/revoked.

## Source of truth

- Roles are read from Supabase JWT `app_metadata`.
- Supported admin markers in backend authorization:
  - `app_metadata.role == "admin"`
  - `app_metadata.roles` contains `"admin"`

## Role definitions

- `user`
  - Can read/update own mapping in settings.
  - Cannot update other users.
  - Gets only own row from `GET /api/settings/users`.

- `admin`
  - Can read all user mappings.
  - Can update any user mapping.

## Assignment policy

1. Admin role is assigned only by technical owner (or delegated platform admin).
2. Role assignment must be tied to a ticket/request with justification.
3. Role change must be logged in change history (date, actor, target user, reason).
4. Temporary admin access must include an expiration date and follow-up removal.

## Operational process

### Grant admin

1. Verify approved request exists.
2. Update Supabase user `app_metadata` with `role: "admin"` (or include in `roles`).
3. Ask user to sign out/sign in again to refresh JWT claims.
4. Validate expected access on settings endpoints.

### Revoke admin

1. Remove `admin` from `app_metadata`.
2. Ask user to sign out/sign in again.
3. Validate that cross-user update returns `403`.

## Security notes

- Do not rely on frontend visibility for authorization; backend checks remain mandatory.
- Keep role model minimal (`user`, `admin`) until more granular permissions are required.
- Prefer short-lived JWTs and explicit refresh after role changes.
