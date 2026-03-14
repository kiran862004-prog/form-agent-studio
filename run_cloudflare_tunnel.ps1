param(
    [int]$LocalPort = 8000,
    [string]$Username = "admin",
    [string]$Password = "change-me-now",
    [switch]$SkipInstall,
    [switch]$NoBrowser
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

function Get-CloudflaredCommand {
    foreach ($candidate in @("cloudflared", "cloudflared.exe")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            return $cmd.Source
        }
    }
    throw "cloudflared was not found on PATH. Install Cloudflare Tunnel first, then rerun this script."
}

$pythonCmd = Get-PythonCommand
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$cloudflaredCmd = Get-CloudflaredCommand

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

$env:FORM_AGENT_USERNAME = $Username
$env:FORM_AGENT_PASSWORD = $Password

Write-Host "Starting local Form Agent Studio on http://127.0.0.1:$LocalPort with basic auth enabled..."
$serverProcess = Start-Process -FilePath $venvPython -ArgumentList @("-m", "form_agent.webapp", "--host", "127.0.0.1", "--port", "$LocalPort") -WorkingDirectory $repoRoot -PassThru

Start-Sleep -Seconds 3

if ($serverProcess.HasExited) {
    throw "The local web server exited early. Check the console for Python errors."
}

Write-Host "Starting Cloudflare quick tunnel..."
Write-Host "When the public trycloudflare.com URL appears below, share that URL with users."
Write-Host "Login will still require the username and password you set in this script."
Write-Host "Username: $Username"
Write-Host "Password: $Password"

if (-not $NoBrowser) {
    Start-Process powershell -ArgumentList @(
        "-NoProfile",
        "-WindowStyle", "Hidden",
        "-Command", "Start-Sleep -Seconds 4; Start-Process 'http://127.0.0.1:$LocalPort'"
    ) | Out-Null
}

try {
    & $cloudflaredCmd tunnel --url "http://127.0.0.1:$LocalPort"
}
finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force
    }
}
