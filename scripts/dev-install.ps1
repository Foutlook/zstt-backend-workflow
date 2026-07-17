[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$pluginName = "zztt-backend-workflow"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$sourcePlugin = (Resolve-Path -LiteralPath (Join-Path $repoRoot "plugins\$pluginName")).Path
$personalPluginsRoot = [System.IO.Path]::GetFullPath((Join-Path $env:USERPROFILE "plugins"))
$targetPlugin = [System.IO.Path]::GetFullPath((Join-Path $personalPluginsRoot $pluginName))
$personalMarketplace = Join-Path $env:USERPROFILE ".agents\plugins\marketplace.json"
$creatorRoot = Join-Path $env:USERPROFILE ".codex\skills\.system\plugin-creator"
$scaffold = Join-Path $creatorRoot "scripts\create_basic_plugin.py"
$cachebuster = Join-Path $creatorRoot "scripts\update_plugin_cachebuster.py"
$validator = Join-Path $creatorRoot "scripts\validate_plugin.py"
$marketplaceReader = Join-Path $creatorRoot "scripts\read_marketplace_name.py"
$python = (Get-Command python -ErrorAction Stop).Source
$codex = (Get-Command codex.cmd -ErrorAction Stop).Source

foreach ($requiredFile in @($scaffold, $cachebuster, $validator, $marketplaceReader)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required Codex plugin-creator file not found: $requiredFile"
    }
}

& (Join-Path $PSScriptRoot "validate.ps1")

$marketplaceEntry = $null
if (Test-Path -LiteralPath $personalMarketplace -PathType Leaf) {
    $marketplace = Get-Content -LiteralPath $personalMarketplace -Encoding UTF8 -Raw | ConvertFrom-Json
    $marketplaceEntry = $marketplace.plugins | Where-Object { $_.name -eq $pluginName } | Select-Object -First 1
}

if ($null -eq $marketplaceEntry) {
    if ((Test-Path -LiteralPath $targetPlugin) -and
        (Get-ChildItem -LiteralPath $targetPlugin -Force | Select-Object -First 1)) {
        throw "Personal plugin directory exists but is not registered in the personal marketplace: $targetPlugin"
    }

    & $python $scaffold $pluginName --path $personalPluginsRoot --with-skills --with-marketplace
    if ($LASTEXITCODE -ne 0) {
        throw "Personal plugin initialization failed with exit code $LASTEXITCODE"
    }
}
elseif ($marketplaceEntry.source.path -ne "./plugins/$pluginName") {
    throw "Unexpected personal marketplace plugin source: $($marketplaceEntry.source.path)"
}

if (-not (Test-Path -LiteralPath $targetPlugin -PathType Container)) {
    New-Item -ItemType Directory -Path $targetPlugin | Out-Null
}

$targetPrefix = $personalPluginsRoot.TrimEnd('\') + '\'
if (-not $targetPlugin.StartsWith($targetPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Personal plugin target escapes the managed plugins directory: $targetPlugin"
}
if ($sourcePlugin.Equals($targetPlugin, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Source plugin and personal plugin target must be different directories."
}

# This directory is a managed build copy. Remove stale files before copying the current source.
Get-ChildItem -LiteralPath $targetPlugin -Force | Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $sourcePlugin -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $targetPlugin -Recurse -Force
}

& $python $cachebuster $targetPlugin
if ($LASTEXITCODE -ne 0) {
    throw "Local plugin cachebuster update failed with exit code $LASTEXITCODE"
}

& $python $validator $targetPlugin
if ($LASTEXITCODE -ne 0) {
    throw "Personal plugin copy validation failed with exit code $LASTEXITCODE"
}

$marketplaceName = (& $python $marketplaceReader).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($marketplaceName)) {
    throw "Unable to read the personal marketplace name."
}

& $codex plugin add "$pluginName@$marketplaceName"
if ($LASTEXITCODE -ne 0) {
    throw "Codex plugin installation failed with exit code $LASTEXITCODE"
}

Write-Host "Local development plugin installed: $pluginName@$marketplaceName"
Write-Host "Start a new Codex task to load the updated skills."
