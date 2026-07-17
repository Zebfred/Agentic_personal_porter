# ===========================================================================
# check_our_agent_models.ps1
#
# Purpose: Calls the Python agent model checker script using the correct
#          conda environment. PowerShell equivalent of
#          check_our_agent_models.sh.
# ===========================================================================
$ErrorActionPreference = 'Stop'

# Get absolute path to the directory containing this script
$ScriptDir = $PSScriptRoot

# Call the python checker script using uv (faster than conda run wrapper)
uv run python "$ScriptDir\check_our_agent_models.py"
