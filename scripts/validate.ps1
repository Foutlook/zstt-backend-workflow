[CmdletBinding()]
param(
    [switch]$SkipTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pluginRoot = Join-Path $repoRoot "plugins\zztt-backend-workflow"
$validator = Join-Path $env:USERPROFILE ".codex\skills\.system\plugin-creator\scripts\validate_plugin.py"
$python = (Get-Command python -ErrorAction Stop).Source

if (-not (Test-Path -LiteralPath $validator -PathType Leaf)) {
    throw "Codex plugin-creator validator not found: $validator"
}

Push-Location $repoRoot
try {
    if (-not $SkipTests) {
        & $python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) {
            throw "Repository tests failed with exit code $LASTEXITCODE"
        }
    }

    & $python $validator $pluginRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Plugin validation failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "ZZTT plugin validation passed: $pluginRoot"
