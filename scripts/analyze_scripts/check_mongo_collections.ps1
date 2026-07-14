# ===========================================================================
# check_mongo_collections.ps1
#
# Purpose: Helper script to review all MongoDB collections for the
#          Agentic Personal Porter. PowerShell equivalent of
#          check_mongo_collections.sh.
# ===========================================================================
$ErrorActionPreference = 'Stop'

# Get absolute path to the directory containing this script
$ScriptDir = $PSScriptRoot

Write-Host "Activating agentic_porter environment and gathering MongoDB statistics..."
Write-Host "======================================================================="
conda run -n agentic_porter python "$ScriptDir\mongo_collections_overview.py"
