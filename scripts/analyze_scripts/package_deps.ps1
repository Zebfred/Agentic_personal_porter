# ===========================================================================
# package_deps.ps1
#
# Purpose: Given a target package, scans your LOCAL environment to:
#          1. List what the package requires (Forward Dependencies)
#          2. List what installed packages require IT (Reverse Dependencies)
#
# Usage:   .\scripts\analyze_scripts\package_deps.ps1 <package_name>
# Example: .\scripts\analyze_scripts\package_deps.ps1 protobuf
#
# PowerShell equivalent of package_deps.sh.
# ===========================================================================
param(
    [Parameter(Mandatory = $false, Position = 0)]
    [string]$PackageName
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($PackageName)) {
    Write-Host "❌ Error: Please provide a package name."
    Write-Host "Usage: .\package_deps.ps1 <package_name>"
    exit 1
}

python -c @"
import sys
import re
from importlib.metadata import distributions, requires, PackageNotFoundError

target_pkg = sys.argv[1].lower()

print(f'==========================================================')
print(f' Dependency Inspector for: \033[1;34m{target_pkg}\033[0m')
print(f'==========================================================\n')

# 1. FORWARD DEPENDENCIES
print(f"\u2b07\ufe0f  What does '{target_pkg}' depend on? (Forward Dependencies)")
try:
    reqs = requires(target_pkg)
    if reqs:
        standard_reqs = [r for r in reqs if 'extra ==' not in r]
        if standard_reqs:
            for r in standard_reqs:
                print(f'  \u251c\u2500\u2500 {r}')
        else:
            print('  \u2514\u2500\u2500 [No core dependencies, only extras]')
    else:
        print('  \u2514\u2500\u2500 [No dependencies]')
except PackageNotFoundError:
    print(f"  \u2514\u2500\u2500 [Package '{target_pkg}' is not installed locally]")

print('\n')

# 2. REVERSE DEPENDENCIES
print(f"\u2b06\ufe0f  Who depends on '{target_pkg}'? (Reverse Dependencies)")

reverse_deps = []
for dist in distributions():
    dist_name = dist.metadata.get('Name')
    if not dist_name:
        continue

    # Skip checking the package against itself
    if dist_name.lower() == target_pkg:
        continue

    dist_reqs = dist.requires
    if not dist_reqs:
        continue

    for r in dist_reqs:
        # Extract the base package name from the requirement string
        # e.g., 'protobuf (>=3.19.0)' -> 'protobuf'
        base_pkg = re.split(r'[<>=~! ;()]', r)[0].strip().lower()

        if base_pkg == target_pkg:
            # We found a package that depends on our target!
            # Strip environment markers (like '; python_version < "3.10"') for cleaner output
            clean_req = r.split(';')[0].strip()
            reverse_deps.append(f'  \u251c\u2500\u2500 {dist_name} \033[1;30m(demands {clean_req})\033[0m')

if reverse_deps:
    # Print alphabetically sorted to make it easy to read
    for dep in sorted(reverse_deps, key=str.lower):
        print(dep)
else:
    print(f"  \u2514\u2500\u2500 [No installed packages depend on '{target_pkg}']")

print('\nDone!')
"@ $PackageName
