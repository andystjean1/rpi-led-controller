# Installs the status feed on the HP laptop: copies status_server.py to C:\Projects\_status,
# opens port 8740 to the local subnet only, and registers a SYSTEM task that starts at boot.
# HP only: aborts anywhere else.
if ($env:COMPUTERNAME -ne 'DESKTOP-06CD787') { "ABORT: wrong machine"; exit 2 }
$ErrorActionPreference = 'Stop'

$port = 8740
$dir = 'C:\Projects\_status'
$python = 'C:\Program Files\Python312\python.exe'
$taskName = 'hp-status-feed'

New-Item -ItemType Directory -Force $dir | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'status_server.py') $dir -Force

if (-not (Get-NetFirewallRule -DisplayName $taskName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $taskName -Direction Inbound -Protocol TCP -LocalPort $port `
        -RemoteAddress LocalSubnet -Action Allow | Out-Null
}

$action = New-ScheduledTaskAction -Execute $python -Argument "status_server.py --port $port" -WorkingDirectory $dir
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal `
    -Settings $settings -Force | Out-Null

# (Re)start it now
Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 3
Get-ScheduledTask -TaskName $taskName | ForEach-Object { '{0} {1} runs as {2}' -f $_.TaskName, $_.State, $_.Principal.UserId }
