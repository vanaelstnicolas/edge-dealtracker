param(
  [string]$BaseUrl = "http://127.0.0.1:8000/api",
  [string]$Token = "",
  [string]$ExpectedDay = "mon",
  [int]$ExpectedHour = 8,
  [int]$ExpectedMinute = 0,
  [switch]$SendMySummary
)

if (-not $Token) {
  if ($env:DEALTRACKER_BEARER_TOKEN) {
    $Token = $env:DEALTRACKER_BEARER_TOKEN
  }
}

if (-not $Token) {
  Write-Error "Missing bearer token. Pass -Token or set DEALTRACKER_BEARER_TOKEN."
  exit 1
}

$headers = @{ Authorization = "Bearer $Token" }

try {
  $status = Invoke-RestMethod -Method Get -Uri "$BaseUrl/summary/weekly/status" -Headers $headers
} catch {
  Write-Error "Weekly status call failed: $($_.Exception.Message)"
  exit 1
}

Write-Host "Scheduler enabled: $($status.scheduler_enabled)"
Write-Host "Timezone/day/hour/minute: $($status.timezone) $($status.day_of_week) $($status.hour)h:$($status.minute)"
Write-Host "Email provider requested/effective: $($status.email_provider_requested) / $($status.email_provider_effective)"
Write-Host "Graph configured: $($status.graph_configured)"
Write-Host "Graph sender: $($status.graph_sender_user)"
Write-Host "Alert webhook configured: $($status.summary_alert_webhook_configured)"
Write-Host "Alert timeout (s): $($status.summary_alert_timeout_seconds)"

if (-not $status.graph_configured) {
  Write-Error "Graph is not configured. Stop here."
  exit 1
}

if ($status.email_provider_effective -ne "graph") {
  Write-Error "Effective provider is '$($status.email_provider_effective)', expected 'graph'. Stop here."
  exit 1
}

if ($status.day_of_week -ne $ExpectedDay -or [int]$status.hour -ne $ExpectedHour -or [int]$status.minute -ne $ExpectedMinute) {
  Write-Error "Scheduler is '$($status.day_of_week) $($status.hour):$($status.minute)'. Expected '$ExpectedDay ${ExpectedHour}:$ExpectedMinute' per FR6."
  exit 1
}

if (-not $SendMySummary) {
  Write-Host "Status check passed. Re-run with -SendMySummary to send only your own summary email."
  exit 0
}

try {
  $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/summary/me/send" -Headers $headers
} catch {
  Write-Error "Send my summary call failed: $($_.Exception.Message)"
  exit 1
}

Write-Host "Send result -> whatsapp: $($response.whatsapp), email: $($response.email)"
Write-Host "Smoke completed."
