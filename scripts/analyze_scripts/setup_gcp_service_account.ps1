# ===========================================================================
# setup_gcp_service_account.ps1
#
# Purpose: Creates the porter-compute-sa service account and binds the
#          Compute Instance Admin (v1) role. Uses Application Default
#          Credentials (ADC) via `gcloud auth application-default login`
#          instead of downloading a JSON key file.
#          PowerShell equivalent of setup_gcp_service_account.sh.
# ===========================================================================
$ErrorActionPreference = 'Stop'

# Source project ID from .auth/.env — NEVER hardcode GCP project IDs
$ScriptDir = $PSScriptRoot
# Navigate up two levels: analyze_scripts → scripts → project_root
$ProjectRoot = Split-Path (Split-Path $ScriptDir -Parent) -Parent
$EnvFile = Join-Path $ProjectRoot ".auth\.env"

$ProjectId = $null
if (Test-Path $EnvFile) {
    # Read .env, skip comments, find PROJECT_ID line, extract value, strip quotes
    $line = Get-Content $EnvFile |
        Where-Object { $_ -notmatch '^\s*#' -and $_ -match 'PROJECT_ID' } |
        Select-Object -First 1
    if ($line) {
        $ProjectId = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")
    }
}

if ([string]::IsNullOrWhiteSpace($ProjectId)) {
    Write-Host "❌ ERROR: PROJECT_ID is not set. Add it to .auth/.env"
    exit 1
}

$SaName = "porter-compute-sa"
$SaEmail = "${SaName}@${ProjectId}.iam.gserviceaccount.com"

Write-Host "=========================================================="
Write-Host "🛡️ PROVISIONING GCP SERVICE ACCOUNT: $SaName"
Write-Host "=========================================================="

Write-Host "[1/2] Creating Service Account: $SaEmail"
# Attempt creation — only suppress "already exists" errors (code 409)
$createOutput = gcloud iam service-accounts create $SaName `
    --description="Dedicated Service Account for Agentic Porter local compute management" `
    --display-name="Agentic Porter Compute SA" `
    --project=$ProjectId 2>&1
if ($LASTEXITCODE -ne 0) {
    if ($createOutput -match 'already exists') {
        Write-Host "Service account already exists. Skipping creation..."
    } else {
        Write-Host "❌ ERROR creating service account: $createOutput"
        exit 1
    }
}

Write-Host ""
Write-Host "[2/2] Binding Compute Instance Admin (v1) Role..."
gcloud projects add-iam-policy-binding $ProjectId `
    --member="serviceAccount:${SaEmail}" `
    --role="roles/compute.instanceAdmin.v1" `
    --condition=None

Write-Host "=========================================================="
Write-Host "✅ SUCCESS! Service Account provisioned."
Write-Host ""
Write-Host "For local development, authenticate via ADC:"
Write-Host "  gcloud auth application-default login"
Write-Host ""
Write-Host "For production (Cloud Run), attach this SA to the service."
Write-Host "=========================================================="
