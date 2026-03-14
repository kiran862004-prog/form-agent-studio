param(
    [Parameter(Mandatory = $true)]
    [string]$Url,
    [switch]$Headed,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Get-PythonCommand {
    foreach ($candidate in @("py", "python", "python3")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            return $candidate
        }
    }
    throw "Python was not found on PATH. Install Python 3.10+ and rerun this script."
}

$pythonCmd = Get-PythonCommand
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..."
    & $pythonCmd -m venv .venv
}

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment Python was not created successfully at $venvPython"
}

if (-not $SkipInstall) {
    Write-Host "Installing dependencies..."
    & $venvPython -m pip install -r requirements.txt
    & $venvPython -m playwright install chromium
}

$args = @(
    "-m", "form_agent.cli",
    "analyze-google",
    "--url", $Url,
    "--schema-out", (Join-Path $repoRoot "output\google_form_schema.json"),
    "--summary-out", (Join-Path $repoRoot "output\google_form_schema.md")
)

if ($Headed) {
    $args += "--headed"
}

Write-Host "Analyzing Google Form in read-only mode..."
& $venvPython @args
