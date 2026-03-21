#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   GITHUB_TOKEN=... ./apply-branch-protection.sh OWNER REPO [BRANCH]
# Example:
#   GITHUB_TOKEN=ghp_xxx ./apply-branch-protection.sh acme dealtracker master

OWNER="${1:-}"
REPO="${2:-}"
BRANCH="${3:-master}"

if [[ -z "$OWNER" || -z "$REPO" ]]; then
  echo "Usage: GITHUB_TOKEN=... $0 OWNER REPO [BRANCH]"
  exit 1
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Missing GITHUB_TOKEN"
  exit 1
fi

API_URL="https://api.github.com/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection"

curl -sS -X PUT "$API_URL" \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -d @- <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Backend Tests",
      "Backend Smoke",
      "Frontend Build"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
JSON

echo
echo "Branch protection applied to ${OWNER}/${REPO}:${BRANCH}"
