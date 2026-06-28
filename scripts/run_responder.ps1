param(
    [switch]$Send,
    [switch]$DryRun,
    [switch]$Draft
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$args = @("-m", "gmail_autoresponder")
if ($DryRun) {
    $args += "--dry-run"
} elseif ($Draft) {
    # Default CLI mode creates drafts when --send is omitted.
} else {
    $args += "--send"
}

& $pythonExe @args
