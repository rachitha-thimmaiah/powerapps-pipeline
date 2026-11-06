# Exports one unmanaged solution from L48 DEV, unpacks it for git, and enables its catalog entry.
# Run this from the developer machine after changing the canvas app, flow, or Dataverse schema.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z][A-Za-z0-9_]{0,99}$')]
    [string] $SolutionName,

    [Parameter(Mandatory = $true)]
    [string] $EnvironmentUrl,

    [string] $DisplayName = "",

    [string] $BranchName = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Pac {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $PacArgs
    )

    Write-Host "pac $($PacArgs -join ' ')"
    & pac @PacArgs
    if ($LASTEXITCODE -ne 0) {
        throw "pac failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $PythonArgs
    )

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & python @PythonArgs
    }
    else {
        $py = Get-Command py -ErrorAction SilentlyContinue
        if (-not $py) {
            throw "Python is required to update catalog/solutions.json."
        }
        & py -3 @PythonArgs
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Python failed with exit code $LASTEXITCODE"
    }
}

if (-not (Get-Command pac -ErrorAction SilentlyContinue)) {
    throw "Install Power Platform CLI first: dotnet tool install --global Microsoft.PowerApps.CLI.Tool"
}

$EnvironmentUrl = $EnvironmentUrl.Trim().TrimEnd("/")
if ($EnvironmentUrl -notmatch '^https://') {
    throw "EnvironmentUrl must be the https Dataverse URL from the Power Platform admin center."
}

if ([string]::IsNullOrWhiteSpace($DisplayName)) {
    $DisplayName = $SolutionName
}

if (-not [string]::IsNullOrWhiteSpace($BranchName)) {
    git -C $RepoRoot checkout -b $BranchName
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create branch $BranchName"
    }
}

$outDir = Join-Path $RepoRoot "out"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$zipPath = Join-Path $outDir "$SolutionName.zip"
$solutionFolder = Join-Path $RepoRoot (Join-Path "solutions" $SolutionName)
New-Item -ItemType Directory -Force -Path $solutionFolder | Out-Null

& pac auth delete --name l48-dev
Invoke-Pac -PacArgs @(
    "auth", "create",
    "--environment", $EnvironmentUrl,
    "--name", "l48-dev"
)
Invoke-Pac -PacArgs @("auth", "select", "--name", "l48-dev")
Invoke-Pac -PacArgs @(
    "solution", "export",
    "--name", $SolutionName,
    "--path", $zipPath,
    "--overwrite",
    "--async"
)
Invoke-Pac -PacArgs @(
    "solution", "unpack",
    "--zipfile", $zipPath,
    "--folder", $solutionFolder,
    "--packagetype", "Both",
    "--allowWrite",
    "--allowDelete",
    "--clobber"
)

Invoke-Python -PythonArgs @(
    (Join-Path $PSScriptRoot "ci\upsert_catalog.py"),
    "--name", $SolutionName,
    "--display-name", $DisplayName
)

$env:SOLUTION_NAME = $SolutionName
Invoke-Python -PythonArgs @((Join-Path $PSScriptRoot "ci\validate_solution.py"))

Write-Host ""
Write-Host "Unpacked $SolutionName into solutions/$SolutionName"
Write-Host "Suggested branch: feature/$SolutionName/<change-description>"
Write-Host "Review the unpack, then commit the solution folder and catalog/solutions.json."
Write-Host "Do not commit the out/ folder."
