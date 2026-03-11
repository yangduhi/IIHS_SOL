$ErrorActionPreference = 'Stop'
$target = Join-Path $PSScriptRoot 'tools\bootstrap\capture-session.ps1'
& $target @args
exit $LASTEXITCODE
