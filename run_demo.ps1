param(
    [switch]$Cli,
    [int]$Count = 5,
    [ValidateSet("random", "weighted", "ai")]
    [string]$Strategy = "weighted",
    [switch]$Submit,
    [switch]$Headed,
    [switch]$SkipInstall,
    [switch]$WebOnly,
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8000
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
$demoUrl = ([System.Uri](Join-Path $repoRoot "demo\demo_form.html")).AbsoluteUri
$configPath = Join-Path $repoRoot "config.example.json"

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

if ($Cli) {
    $args = @(
        "-m", "form_agent.cli",
        "run",
        "--url", $demoUrl,
        "--count", $Count,
        "--strategy", $Strategy,
        "--config", $configPath,
        "--schema-out", (Join-Path $repoRoot "output\demo_schema.json"),
        "--json-out", (Join-Path $repoRoot "output\demo_responses.json"),
        "--csv-out", (Join-Path $repoRoot "output\demo_responses.csv")
    )

    if ($Submit) {
        $args += "--submit"
        $args += "--confirm-owned-form"
    }
    if ($Headed) {
        $args += "--headed"
    }

    Write-Host "Running CLI demo against $demoUrl"
    & $venvPython @args
    exit $LASTEXITCODE
}

$displayHost = if ($ListenHost -eq "0.0.0.0") { "localhost" } else { $ListenHost }
Write-Host "Starting Form Agent Studio at http://${displayHost}:$Port"
Start-Process powershell -ArgumentList @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-Command", "Start-Sleep -Seconds 2; Start-Process 'http://${displayHost}:$Port'"
) | Out-Null
& $venvPython -m form_agent.webapp --host $ListenHost --port $Port
