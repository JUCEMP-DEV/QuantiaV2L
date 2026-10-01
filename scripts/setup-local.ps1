$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $projectRoot "Backend"
$frontendDir = Join-Path $projectRoot "Frontend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
$tessdataDir = Join-Path $backendDir ".local-tools\tessdata"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python no esta instalado o no esta disponible en PATH."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm no esta instalado o no esta disponible en PATH."
}
if (-not (Get-Command ollama.exe -ErrorAction SilentlyContinue)) {
    throw "Ollama no esta instalado o no esta disponible en PATH."
}
if (-not (Test-Path -LiteralPath (Join-Path $tessdataDir "spa.traineddata") -PathType Leaf)) {
    throw "Falta Backend/.local-tools/tessdata/spa.traineddata. Copia el modelo oficial de Tesseract para espanol."
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    & python -m venv (Join-Path $backendDir ".venv")
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $backendDir "requirements.txt")

Push-Location $frontendDir
try {
    & npm.cmd install --no-audit --no-fund
}
finally {
    Pop-Location
}

foreach ($relativePath in @("Backend\.env.local", "Frontend\.env.local")) {
    $destination = Join-Path $projectRoot $relativePath
    if (-not (Test-Path -LiteralPath $destination)) {
        Copy-Item -LiteralPath "$destination.example" -Destination $destination
        Write-Warning "Se creo $relativePath desde el ejemplo. Completa sus variables de Supabase antes de iniciar."
    }
}

Write-Output "Entorno preparado. Ejecuta scripts\check-local.ps1 y completa las variables pendientes."
