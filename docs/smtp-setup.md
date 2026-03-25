# Email Provider Setup (Microsoft Graph + SMTP fallback)

This project now supports Microsoft Graph as the primary email provider for owner summaries, with optional SMTP fallback.

## Provider strategy

- Primary (production): Microsoft Graph via Entra ID OAuth 2.0 client credentials
- Fallback (temporary): SMTP

Set `EMAIL_PROVIDER` to one of:

- `auto` (default): Graph if configured, otherwise SMTP
- `graph`: Graph first, optional fallback to SMTP
- `smtp`: SMTP only

## Required backend variables (Graph)

Set these values in `backend/.env.local`:

- `EMAIL_PROVIDER=graph` (or `auto`)
- `GRAPH_TENANT_ID`
- `GRAPH_CLIENT_ID`
- `GRAPH_CLIENT_SECRET`
- `GRAPH_SENDER_USER` (mailbox UPN/address used as sender)

Optional Graph tuning:

- `GRAPH_TIMEOUT_SECONDS` (default `20`)
- `GRAPH_FALLBACK_TO_SMTP` (default `true`)

## Optional SMTP fallback variables

Keep these only as fallback while migrating:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_FROM_EMAIL`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_STARTTLS_ENABLED`
- `SMTP_SSL_ENABLED`
- `SMTP_TIMEOUT_SECONDS`

## Scheduler variables

- `WEEKLY_SUMMARY_SCHEDULER_ENABLED`
- `WEEKLY_SUMMARY_TIMEZONE`
- `WEEKLY_SUMMARY_DAY_OF_WEEK`
- `WEEKLY_SUMMARY_HOUR`

## Entra ID / Graph prerequisites

1. Register an Entra application.
2. Grant Microsoft Graph application permission `Mail.Send`.
3. Grant admin consent for the tenant.
4. Ensure `GRAPH_SENDER_USER` mailbox exists and is allowed for app-based sending in your tenant policy.

## Validation steps

1. Restart backend.
2. Call admin endpoint `GET /api/summary/weekly/status`.
3. Confirm:
   - `email_provider_effective` is `graph`
   - `graph_configured` is `true`
4. Trigger manual send via `POST /api/summary/weekly/trigger`.
5. Verify mailbox reception and monitor fallback behavior (if enabled).

## Security notes

- Use a dedicated technical sender mailbox (for example `noreply@...`).
- Never commit Graph client secrets or SMTP passwords.
- Rotate Entra app secret on schedule and after role/team changes.
