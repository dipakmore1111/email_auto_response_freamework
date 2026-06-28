param(
    [string]$TaskName = "Gmail Auto Responder",
    [int]$IntervalMinutes = 15
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $projectRoot "scripts\run_responder.ps1"

if (-not (Test-Path $runner)) {
    throw "Run script not found: $runner"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$runner`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)).Repetition
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Description "Runs the Gmail auto responder on a schedule." -Force | Out-Null
Write-Host "Scheduled task registered: $TaskName"
