param(
    [string]$ListenHost = "0.0.0.0",
    [int]$Port = 8000,
    [string]$Username,
    [string]$Password,
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

if ($Username -and $Password) {
    $env:FORM_AGENT_USERNAME = $Username
    $env:FORM_AGENT_PASSWORD = $Password
    Write-Host "Basic auth enabled for network access."
} else {
    Write-Warning "Starting without basic auth. Anyone who can reach this server can use it."
}

Write-Host "Starting Form Agent Studio on http://$ListenHost`:$Port"
& $venvPython -m form_agent.webapp --host $ListenHost --port $Port
