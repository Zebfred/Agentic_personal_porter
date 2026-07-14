# ===========================================================================
# fetch_nat_static_ip.ps1
#
# Purpose: Diagnoses Cloud Run NAT egress traffic IPs by querying Cloud
#          Routers in us-central1 for static or auto-allocated NAT IPs.
#          PowerShell equivalent of fetch_nat_static_ip.sh.
# ===========================================================================
$ErrorActionPreference = 'Stop'

# Source project ID from .auth/.env — NEVER hardcode GCP project IDs in public repos
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

Write-Host "=========================================================="
Write-Host "🔍 DIAGNOSING CLOUD RUN NAT EGRESS TRAFFIC IP"
Write-Host "=========================================================="

# Find Cloud Routers running in us-central1
$Routers = gcloud compute routers list --project=$ProjectId --regions=us-central1 --format="value(name)"

if ([string]::IsNullOrWhiteSpace($Routers)) {
    Write-Host "❌ No VPC Routers found in us-central1!"
    exit 1
}

Write-Host "Found VPC Router(s): $Routers"
Write-Host "---"

foreach ($Router in ($Routers -split "`n")) {
    $Router = $Router.Trim()
    if ([string]::IsNullOrWhiteSpace($Router)) { continue }

    Write-Host "Checking Router: $Router"

    # Find exact explicitly allocated Static NAT IPs
    $StaticIps = gcloud compute routers get-status $Router --region=us-central1 --project=$ProjectId `
        --format="value(result.natStatus[0].userAllocatedNatIpResources)"

    # Check if they are dynamically allocated instead
    $AutoIps = gcloud compute routers get-status $Router --region=us-central1 --project=$ProjectId `
        --format="value(result.natStatus[0].autoAllocatedNatIps)"

    if (-not [string]::IsNullOrWhiteSpace($StaticIps) -and $StaticIps -ne '[]') {
        Write-Host "✅ Detected Explicitly Bound Cloud NAT Static IPv4(s):"
        Write-Host "   ---> $StaticIps <---"
        Write-Host "⚠️ Ensure THESE exact IPs are whitelisted in your MongoDB Atlas Network Access panel."
    }
    elseif (-not [string]::IsNullOrWhiteSpace($AutoIps) -and $AutoIps -ne '[]') {
        Write-Host "⚠️ Detected AUTO-ALLOCATED NAT IPs:"
        Write-Host "   ---> $AutoIps <---"
        Write-Host "   Note: Auto-allocated IPs can change! It is highly recommended to bind a reserved Static IP to your NAT!"
    }
    else {
        Write-Host "❌ No active outbound NAT IPs detected bound to this router!"
    }
}

Write-Host "=========================================================="
Write-Host "Note: I also verified that your Cloud Run container IS perfectly configured to push '--vpc-egress=all-traffic'!"
Write-Host "If MongoDB is timing out, it is strictly because the IP(s) listed above are not in the Atlas Whitelist."
Write-Host "=========================================================="
