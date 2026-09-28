#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('register', 'remove', 'list')]
    [string]$Action = 'list',
    [string]$Root = ''
)

$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
$runner = Join-Path $Root 'run.ps1'

function New-OpsTask {
    param([string]$Name, [string]$OpsArgs, [string]$Schedule, [string]$Time, [string]$Days)
    $cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`" $OpsArgs"
    $args = @('/Create', '/TN', $Name, '/TR', $cmd, '/F', '/SC', $Schedule)
    if ($Time) { $args += @('/ST', $Time) }
    if ($Days) { $args += @('/D', $Days) }
    & schtasks.exe @args
}

switch ($Action) {
    'register' {
        New-OpsTask -Name 'BelentaniOps-MonitorHourly' -OpsArgs 'monitor'  -Schedule 'HOURLY' -Time '00:05'
        New-OpsTask -Name 'BelentaniOps-BackupDaily'   -OpsArgs 'backup run --yes' -Schedule 'DAILY' -Time '03:30'
        New-OpsTask -Name 'BelentaniOps-ReportWeekly'  -OpsArgs 'run --out reports\weekly.json' -Schedule 'WEEKLY' -Time '08:00' -Days 'MON'
        Write-Host 'Tareas registradas: MonitorHourly, BackupDaily, ReportWeekly'
    }
    'remove' {
        foreach ($n in @('BelentaniOps-MonitorHourly', 'BelentaniOps-BackupDaily', 'BelentaniOps-ReportWeekly')) {
            & schtasks.exe /Delete /TN $n /F 2>$null
        }
        Write-Host 'Tareas eliminadas'
    }
    'list' {
        & schtasks.exe /Query /TN 'BelentaniOps-MonitorHourly' 2>$null
        & schtasks.exe /Query /TN 'BelentaniOps-BackupDaily' 2>$null
        & schtasks.exe /Query /TN 'BelentaniOps-ReportWeekly' 2>$null
    }
}
