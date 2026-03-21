#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   GITHUB_TOKEN=... ./verify-branch-protection.sh OWNER REPO [BRANCH]

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

curl -sS \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection"
