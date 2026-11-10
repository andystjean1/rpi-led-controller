# Registers `shadow-compare-push` on the PC: every 10 minutes it reads the PC's collector run counts
# (read-only, from each project's runs table) and POSTs them to the Pi's monitor page, which lines
# them up against the HP's. Runs as the current user, hidden (pythonw), no window.
# Remove it when the shadow run ends:  Unregister-ScheduledTask shadow-compare-push -Confirm:$false
$ErrorActionPreference = 'Stop'
$python = 'C:\Users\Andy\Projects\nba-edges\env\Scripts\pythonw.exe'
$script = Join-Path $PSScriptRoot 'shadow_counts.py'
$url = 'http://10.0.0.10:8750/api/shadow'
if (-not (Test-Path $python)) { "ABORT: $python not found"; exit 3 }

$action = New-ScheduledTaskAction -Execute $python -Argument ('-I "{0}" --push {1}' -f $script, $url)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName 'shadow-compare-push' -Action $action -Trigger $trigger -Settings $settings `
    -Description 'Pushes the PC collector run counts to the Pi for the shadow-run comparison' -Force | Out-Null
Get-ScheduledTask -TaskName 'shadow-compare-push' | ForEach-Object { '{0} {1}' -f $_.TaskName, $_.State }
