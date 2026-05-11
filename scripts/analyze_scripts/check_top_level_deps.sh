#!/bin/bash
set -euo pipefail

# ============================================================================
# check_top_level_deps.sh
# 
# Purpose: Inspects the locally installed top-level packages and extracts their 
#          exact dependency version constraints (the minimum required ranges) 
#          using Python's native importlib.metadata.
# ============================================================================

echo "=========================================================="
echo " Dependency Requirement Inspector for Top-Level Packages"
echo "=========================================================="

# Group 1: Google/Auth
declare -a GOOGLE_AUTH=(
    "google-api-python-client" 
    "google-auth" 
    "google-api-core" 
    "proto-plus" 
    "protobuf"
)

# Group 2: LangChain & AI Tooling
declare -a LANGCHAIN_AI=(
    "crewai" 
    "crewai-tools" 
    "langchain" 
    "langchain-core" 
    "langchain-mongodb" 
    "chromadb"
)

# Group 3: TensorFlow/Keras
declare -a TENSORFLOW_KERAS=(
    "tf-keras" 
    "tensorflow" 
    "onnxruntime"
)

# Function to inspect a package using Python's importlib.metadata
inspect_pkg() {
    local pkg="$1"
    echo -e "\n📦 \033[1;34m${pkg}\033[0m"
    
    # We use python -c to cleanly parse the installed metadata for exact ranges
    python -c "
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
" "$pkg"
}

# --- Execution ---

echo -e "\n\033[1;33m=== Google/Auth Group ===\033[0m"
for pkg in "${GOOGLE_AUTH[@]}"; do
    inspect_pkg "$pkg"
done

echo -e "\n\033[1;33m=== LangChain & AI Tooling ===\033[0m"
for pkg in "${LANGCHAIN_AI[@]}"; do
    inspect_pkg "$pkg"
done

echo -e "\n\033[1;33m=== TensorFlow/Keras ===\033[0m"
for pkg in "${TENSORFLOW_KERAS[@]}"; do
    inspect_pkg "$pkg"
done

echo ""
echo "Done!"
