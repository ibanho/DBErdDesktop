$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Virtual environment not found. Create it first: .\.python\3.14.5\python.exe -m venv .venv"
}

& $python -m pip install -r (Join-Path $PSScriptRoot "requirements-exe.txt")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $python -m PyInstaller --noconfirm (Join-Path $PSScriptRoot "DBErdDesktop.spec")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Built executable:" (Join-Path $PSScriptRoot "dist\DBErdDesktop.exe")
