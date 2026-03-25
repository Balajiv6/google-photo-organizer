# ---------------------------------------------------------------------------
# startup.ps1 — launch google-photos-organizer (Windows PowerShell)
# ---------------------------------------------------------------------------
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# --------------------------------------------------------------------------- #
# Activate virtual environment if one exists
# --------------------------------------------------------------------------- #
foreach ($venvDir in @("venv", ".venv")) {
    $activateScript = Join-Path $ScriptDir "$venvDir\Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        Write-Host "[startup] Activating virtual environment: $venvDir"
        & $activateScript
        break
    }
}

# --------------------------------------------------------------------------- #
# Ensure dependencies are installed
# --------------------------------------------------------------------------- #
pip install -q -r (Join-Path $ScriptDir "requirements.txt")

# --------------------------------------------------------------------------- #
# Run the organiser
# Override dry-run via env var before calling this script:
#   $env:ORGANIZER_DRY_RUN = "false"; .\startup.ps1
# --------------------------------------------------------------------------- #
Write-Host "[startup] Starting google-photos-organizer ..."
$env:PYTHONPATH = Join-Path $ScriptDir "src"
python (Join-Path $ScriptDir "src\main.py") @args
