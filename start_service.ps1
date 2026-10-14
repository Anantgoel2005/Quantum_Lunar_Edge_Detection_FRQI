$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$variantPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $variantPython)) {
    throw 'Create .venv and install requirements-real-case.txt first; see README.md.'
}
& $variantPython visualization/build_real_case_view.py
if ($LASTEXITCODE -ne 0) { throw 'Unable to build the local view' }
& $variantPython visualization/real_case_server.py
