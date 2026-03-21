param(
  [Parameter(Mandatory = $true)][string]$Owner,
  [Parameter(Mandatory = $true)][string]$Repo,
  [string]$Branch = "master"
)

if (-not $env:GITHUB_TOKEN) {
  Write-Error "Missing GITHUB_TOKEN environment variable"
  exit 1
}

$url = "https://api.github.com/repos/$Owner/$Repo/branches/$Branch/protection"

$headers = @{
  Accept                 = "application/vnd.github+json"
  Authorization          = "Bearer $($env:GITHUB_TOKEN)"
  "X-GitHub-Api-Version" = "2022-11-28"
}

Invoke-RestMethod -Method Get -Uri $url -Headers $headers
