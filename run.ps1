#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$python = $null
foreach ($candidate in @('python', 'py')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source; break }
}
if (-not $python) {
    Write-Error 'No se encontro python en PATH'
    exit 127
}

$env:PYTHONPATH = $root
if ($Args.Count -eq 0) {
    & $python -m belentani_ops run
} else {
    & $python -m belentani_ops @Args
}
exit $LASTEXITCODE
