#Requires -Version 5.1
# Meridian capstone — Windows setup. Idempotent: checks each prerequisite and
# installs only what's missing via winget, then wires the project and runs the
# green light. Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
$ErrorActionPreference = "Stop"

function Ensure-WingetPackage($Id, $Name) {
    winget list --id $Id -e *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[ok] $Name already installed"
    } else {
        Write-Host "[..] installing $Name ($Id)"
        winget install -e --id $Id --silent --accept-package-agreements --accept-source-agreements --no-upgrade
        if ($LASTEXITCODE -ne 0) { throw "winget failed to install $Name ($Id)" }
        Write-Host "[ok] installed $Name"
    }
}

Write-Host "== Meridian capstone setup =="

# 1. Prerequisites (verified winget ids)
Ensure-WingetPackage "Python.Python.3.12"        "Python 3.12"
Ensure-WingetPackage "Git.Git"                   "Git"
Ensure-WingetPackage "OpenJS.NodeJS.LTS"         "Node.js LTS"
Ensure-WingetPackage "Microsoft.VisualStudioCode" "VS Code"

# refresh PATH so freshly installed tools are visible in this session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

# 2. Claude Code (ships over npm; needs Node). Optional — the Python kit needs
# no Node, so a missing npm warns and skips rather than blocking setup.
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "[..] installing Claude Code (npm)"
    npm install -g "@anthropic-ai/claude-code"
} else {
    Write-Host "[warn] npm not found — skipping Claude Code CLI install. Install Node LTS + 'npm i -g @anthropic-ai/claude-code' later if you want the CLI."
}

# 3. Python project (venv + pinned deps)
Write-Host "[..] creating venv and installing deps"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# 4. VS Code extensions
Write-Host "[..] installing VS Code extensions"
code --install-extension ms-python.python --force
code --install-extension anthropic.claude-code --force

# 5. .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[!!] Created .env — open it and paste your ANTHROPIC_API_KEY, then re-run to complete the API check."
}

# 6. Green light
Write-Host "== running green light (pytest) =="
if ((Get-Content ".env" | Where-Object { $_ -match "^ANTHROPIC_API_KEY=.+" })) {
    $key = ((Get-Content ".env" | Where-Object { $_ -match "^ANTHROPIC_API_KEY=" }) -replace "^ANTHROPIC_API_KEY=","").Trim()
    $env:ANTHROPIC_API_KEY = $key
    .\.venv\Scripts\python.exe -m pytest -q
    Write-Host "== READY: environment green (including live API) =="
} else {
    .\.venv\Scripts\python.exe -m pytest -m "not api" -q
    Write-Host "== Offline checks green. Add your ANTHROPIC_API_KEY to .env and re-run for the mandatory API check. =="
}
