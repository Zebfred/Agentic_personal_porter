# ===========================================================================
# check_top_level_deps.ps1
#
# Purpose: Inspects the locally installed top-level packages and extracts
#          their exact dependency version constraints (the minimum required
#          ranges) using Python's native importlib.metadata.
#          PowerShell equivalent of check_top_level_deps.sh.
# ===========================================================================
$ErrorActionPreference = 'Stop'

Write-Host "=========================================================="
Write-Host " Dependency Requirement Inspector for Top-Level Packages"
Write-Host "=========================================================="

# Group 1: Google/Auth
$GoogleAuth = @(
    "google-api-python-client"
    "google-auth"
    "google-api-core"
    "proto-plus"
    "protobuf"
)

# Group 2: LangChain & AI Tooling
$LangchainAI = @(
    "crewai"
    "crewai-tools"
    "langchain"
    "langchain-core"
    "langchain-mongodb"
    "chromadb"
)

# Group 3: TensorFlow/Keras
$TensorflowKeras = @(
    "tf-keras"
    "tensorflow"
    "onnxruntime"
)

# Function to inspect a package using Python's importlib.metadata
function Invoke-InspectPackage {
    param(
        [Parameter(Mandatory)]
        [string]$PackageName
    )

    Write-Host ""
    Write-Host -NoNewline "📦 "
    Write-Host -ForegroundColor Blue "$PackageName"

    # Use python -c to cleanly parse the installed metadata for exact ranges
    python -c @"
import sys
from importlib.metadata import requires, PackageNotFoundError

pkg = sys.argv[1]
try:
    reqs = requires(pkg)
    if reqs:
        # Edge Case handling: Only print standard dependencies, skip 'extras' (like testing/dev deps)
        standard_reqs = [r for r in reqs if 'extra ==' not in r]

        if standard_reqs:
            for r in standard_reqs:
                print(f'  ├── {r}')
        else:
            print('  └── [No core dependencies, only extras]')
    else:
        print('  └── [No dependencies]')
except PackageNotFoundError:
    print('  └── [Package not installed locally]')
"@ $PackageName
}

# --- Execution ---

Write-Host ""
Write-Host -ForegroundColor Yellow "=== Google/Auth Group ==="
foreach ($pkg in $GoogleAuth) {
    Invoke-InspectPackage -PackageName $pkg
}

Write-Host ""
Write-Host -ForegroundColor Yellow "=== LangChain & AI Tooling ==="
foreach ($pkg in $LangchainAI) {
    Invoke-InspectPackage -PackageName $pkg
}

Write-Host ""
Write-Host -ForegroundColor Yellow "=== TensorFlow/Keras ==="
foreach ($pkg in $TensorflowKeras) {
    Invoke-InspectPackage -PackageName $pkg
}

Write-Host ""
Write-Host "Done!"
