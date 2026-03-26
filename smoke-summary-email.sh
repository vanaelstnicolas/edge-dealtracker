#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000/api}"
TOKEN="${DEALTRACKER_BEARER_TOKEN:-}"
SEND_MY_SUMMARY="${SEND_MY_SUMMARY:-false}"
EXPECTED_DAY="${EXPECTED_DAY:-mon}"
EXPECTED_HOUR="${EXPECTED_HOUR:-8}"
EXPECTED_MINUTE="${EXPECTED_MINUTE:-0}"

if [[ -z "$TOKEN" ]]; then
  echo "Missing DEALTRACKER_BEARER_TOKEN"
  exit 1
fi

STATUS_JSON="$(curl -fsS -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/summary/weekly/status")"

python - "$STATUS_JSON" "$SEND_MY_SUMMARY" "$BASE_URL" "$TOKEN" "$EXPECTED_DAY" "$EXPECTED_HOUR" "$EXPECTED_MINUTE" <<'PY'
import json
import subprocess
import sys

status = json.loads(sys.argv[1])
send_my_summary = sys.argv[2].lower() == "true"
base_url = sys.argv[3]
token = sys.argv[4]
expected_day = sys.argv[5]
expected_hour = int(sys.argv[6])
expected_minute = int(sys.argv[7])

print(f"Scheduler enabled: {status.get('scheduler_enabled')}")
print(f"Timezone/day/hour/minute: {status.get('timezone')} {status.get('day_of_week')} {status.get('hour')}h:{status.get('minute')}")
print(f"Email provider requested/effective: {status.get('email_provider_requested')} / {status.get('email_provider_effective')}")
print(f"Graph configured: {status.get('graph_configured')}")
print(f"Graph sender: {status.get('graph_sender_user')}")
print(f"Alert webhook configured: {status.get('summary_alert_webhook_configured')}")
print(f"Alert timeout (s): {status.get('summary_alert_timeout_seconds')}")

if not status.get("graph_configured"):
    print("Graph is not configured. Stop here.")
    raise SystemExit(1)

if status.get("email_provider_effective") != "graph":
    print(f"Effective provider is '{status.get('email_provider_effective')}', expected 'graph'. Stop here.")
    raise SystemExit(1)

if (
    status.get("day_of_week") != expected_day
    or int(status.get("hour", -1)) != expected_hour
    or int(status.get("minute", -1)) != expected_minute
):
    print(
        f"Scheduler is '{status.get('day_of_week')} {status.get('hour')}:{status.get('minute')}'. "
        f"Expected '{expected_day} {expected_hour}:{expected_minute}' per FR6."
    )
    raise SystemExit(1)

if not send_my_summary:
    print("Status check passed. Re-run with SEND_MY_SUMMARY=true to send only your own summary email.")
    raise SystemExit(0)

proc = subprocess.run(
    [
        "curl",
        "-fsS",
        "-X",
        "POST",
        "-H",
        f"Authorization: Bearer {token}",
        f"{base_url}/summary/me/send",
    ],
    check=True,
    capture_output=True,
    text=True,
)

send_result = json.loads(proc.stdout)
print(f"Send result -> whatsapp: {send_result.get('whatsapp')}, email: {send_result.get('email')}")
print("Smoke completed.")
PY
