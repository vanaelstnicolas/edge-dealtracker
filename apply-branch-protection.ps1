param(
  [Parameter(Mandatory = $true)][string]$Owner,
  [Parameter(Mandatory = $true)][string]$Repo,
  [string]$Branch = "master"
)

# Usage:
#   $env:GITHUB_TOKEN = "ghp_xxx"
#   .\apply-branch-protection.ps1 -Owner "acme" -Repo "dealtracker" -Branch "master"

if (-not $env:GITHUB_TOKEN) {
  Write-Error "Missing GITHUB_TOKEN environment variable"
  exit 1
}

$url = "https://api.github.com/repos/$Owner/$Repo/branches/$Branch/protection"

$body = @{
  required_status_checks = @{
    strict   = $true
    contexts = @("Backend Tests", "Backend Smoke", "Business E2E Smoke", "Frontend Build")
  }
  enforce_admins = $true
  required_pull_request_reviews = @{
    dismiss_stale_reviews           = $true
    require_code_owner_reviews      = $false
    required_approving_review_count = 1
  }
  restrictions                   = $null
  required_linear_history        = $false
  allow_force_pushes             = $false
  allow_deletions                = $false
  block_creations                = $false
  required_conversation_resolution = $true
  lock_branch                    = $false
  allow_fork_syncing             = $true
} | ConvertTo-Json -Depth 10

$headers = @{
  Accept                 = "application/vnd.github+json"
  Authorization          = "Bearer $($env:GITHUB_TOKEN)"
  "X-GitHub-Api-Version" = "2022-11-28"
}

Invoke-RestMethod -Method Put -Uri $url -Headers $headers -Body $body -ContentType "application/json" | Out-Null

Write-Host "Branch protection applied to ${Owner}/${Repo}:${Branch}"

