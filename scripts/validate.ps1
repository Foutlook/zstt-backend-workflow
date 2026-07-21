[CmdletBinding()]
param(
    [switch]$SkipTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = (Get-Command python -ErrorAction Stop).Source
$uv = (Get-Command uv -ErrorAction Stop).Source
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("zstt-cli-build-" + [guid]::NewGuid().ToString("N"))
$buildSource = Join-Path $temporaryRoot "source"
$wheelRoot = Join-Path $temporaryRoot "wheel"

Push-Location $repoRoot
try {
    & $python -X utf8 (Join-Path $repoRoot "scripts\validate_skills.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Skill validation failed with exit code $LASTEXITCODE"
    }

    if (-not $SkipTests) {
        & $python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) {
            throw "Repository tests failed with exit code $LASTEXITCODE"
        }
    }

    & $python -m compileall -q src
    if ($LASTEXITCODE -ne 0) {
        throw "Python source compilation failed with exit code $LASTEXITCODE"
    }

    New-Item -ItemType Directory -Path $buildSource | Out-Null
    New-Item -ItemType Directory -Path $wheelRoot | Out-Null
    foreach ($file in @("pyproject.toml", "MANIFEST.in", "README.md")) {
        Copy-Item -LiteralPath (Join-Path $repoRoot $file) -Destination $buildSource
    }
    Copy-Item -LiteralPath (Join-Path $repoRoot "src") -Destination $buildSource -Recurse
    # Test execution creates bytecode caches; they are never part of project-level Skill resources.
    Get-ChildItem -LiteralPath (Join-Path $buildSource "src") -Directory -Recurse -Filter __pycache__ | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }

    Push-Location $buildSource
    try {
        & $uv build --wheel --no-build-logs --no-create-gitignore --out-dir $wheelRoot .
        if ($LASTEXITCODE -ne 0) {
            throw "Wheel build failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }

    $wheels = @(Get-ChildItem -LiteralPath $wheelRoot -Filter *.whl -File)
    if ($wheels.Count -ne 1) {
        throw "Expected exactly one wheel, found $($wheels.Count)"
    }
    & $python (Join-Path $repoRoot "scripts\verify_wheel.py") $wheels[0].FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Wheel content verification failed with exit code $LASTEXITCODE"
    }

    $venvRoot = Join-Path $temporaryRoot "venv"
    $smokeProject = Join-Path $temporaryRoot "business-repo"
    & $python -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Validation virtual environment creation failed with exit code $LASTEXITCODE"
    }
    $venvPython = Join-Path $venvRoot "Scripts\python.exe"
    $zstt = Join-Path $venvRoot "Scripts\zstt.exe"
    & $venvPython -m pip install --no-deps $wheels[0].FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Wheel installation failed with exit code $LASTEXITCODE"
    }
    & $zstt version
    if ($LASTEXITCODE -ne 0) {
        throw "Installed zstt entry point failed with exit code $LASTEXITCODE"
    }
    New-Item -ItemType Directory -Path $smokeProject | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $smokeProject ".git") | Out-Null
    & $zstt init $smokeProject
    if ($LASTEXITCODE -ne 0) {
        throw "Installed zstt init smoke test failed with exit code $LASTEXITCODE"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $smokeProject ".agents\skills\zstt-requirement-clarification\SKILL.md"))) {
        throw "Installed wheel did not initialize project-level ZSTT Skills"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $smokeProject ".zstt-kit\runtime\rule_resolver.py"))) {
        throw "Installed wheel did not initialize ZSTT rules runtime"
    }
    & $zstt doctor $smokeProject --json
    if ($LASTEXITCODE -ne 0) {
        throw "Installed zstt doctor smoke test failed with exit code $LASTEXITCODE"
    }
    & $venvPython (Join-Path $smokeProject ".zstt-kit\runtime\rule_resolver.py") check
    if ($LASTEXITCODE -ne 0) {
        throw "Installed ZSTT rule resolver failed catalog validation with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}

Write-Host "ZSTT CLI validation passed: $repoRoot"
