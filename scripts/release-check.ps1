[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pluginName = "zztt-backend-workflow"
$pluginManifestPath = Join-Path $repoRoot "plugins\$pluginName\.codex-plugin\plugin.json"
$marketplacePath = Join-Path $repoRoot ".agents\plugins\marketplace.json"

& (Join-Path $PSScriptRoot "validate.ps1")

$pluginManifest = Get-Content -LiteralPath $pluginManifestPath -Encoding UTF8 -Raw | ConvertFrom-Json
$marketplace = Get-Content -LiteralPath $marketplacePath -Encoding UTF8 -Raw | ConvertFrom-Json
$marketplaceEntry = $marketplace.plugins | Where-Object { $_.name -eq $pluginName } | Select-Object -First 1

if ($pluginManifest.name -ne $pluginName) {
    throw "plugin.json name does not match the plugin directory: $($pluginManifest.name)"
}
if ($pluginManifest.version -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$') {
    throw "Release version must be semantic and must not contain a cachebuster: $($pluginManifest.version)"
}
if ($marketplace.name -ne "zztt-team") {
    throw "Team marketplace name must be zztt-team: $($marketplace.name)"
}
if ($null -eq $marketplaceEntry) {
    throw "Team marketplace is missing plugin entry: $pluginName"
}
if ($marketplaceEntry.source.path -ne "./plugins/$pluginName") {
    throw "Team marketplace plugin path is invalid: $($marketplaceEntry.source.path)"
}

Write-Host "Release checks passed: $pluginName $($pluginManifest.version)"
