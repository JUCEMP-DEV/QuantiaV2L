$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $projectRoot "Backend"
$frontendDir = Join-Path $projectRoot "Frontend"
$runtimeDir = Join-Path $projectRoot ".local-runtime"
$pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw "Falta Backend/.venv. Ejecuta scripts/setup-local.ps1."
}
if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules") -PathType Container)) {
    throw "Faltan dependencias del frontend. Ejecuta scripts/setup-local.ps1."
}
foreach ($envFile in @("Backend\.env.local", "Frontend\.env.local")) {
    $path = Join-Path $projectRoot $envFile
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Falta $envFile. Copia el archivo .example y completa Supabase."
    }
    if (Select-String -LiteralPath $path -Pattern "REEMPLAZAR|TU_PROYECTO" -Quiet) {
        throw "$envFile contiene valores pendientes. Completa Supabase y los secretos locales."
    }
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
}
catch {
    $ollamaExe = (Get-Command ollama.exe -ErrorAction Stop).Source
    $ollamaProcess = Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimeDir "ollama.out.log") `
        -RedirectStandardError (Join-Path $runtimeDir "ollama.err.log")
    Set-Content -LiteralPath (Join-Path $runtimeDir "ollama.pid") -Value $ollamaProcess.Id
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
            break
        }
        catch {
            if ($attempt -eq 19) { throw "Ollama no inicio. Revisa .local-runtime/ollama.err.log." }
        }
    }
}

$tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
if (@($tags.models | ForEach-Object { $_.name }) -notcontains "llama3.2:3b") {
    throw "Falta llama3.2:3b. Ejecuta: ollama pull llama3.2:3b"
}

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 | Out-Null
}
catch {
    $backendProcess = Start-Process -FilePath $pythonExe `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimeDir "backend.out.log") `
        -RedirectStandardError (Join-Path $runtimeDir "backend.err.log")
    Set-Content -LiteralPath (Join-Path $runtimeDir "backend.pid") -Value $backendProcess.Id
}

try {
    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5173" -TimeoutSec 2 | Out-Null
}
catch {
    $npmExe = (Get-Command npm.cmd -ErrorAction Stop).Source
    $frontendProcess = Start-Process -FilePath $npmExe -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1") `
        -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimeDir "frontend.out.log") `
        -RedirectStandardError (Join-Path $runtimeDir "frontend.err.log")
    Set-Content -LiteralPath (Join-Path $runtimeDir "frontend.pid") -Value $frontendProcess.Id
}

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 | Out-Null
        Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5173" -TimeoutSec 2 | Out-Null
        Write-Output "Quantia V2 Local esta activa: http://127.0.0.1:5173"
        exit 0
    }
    catch {
        if ($attempt -eq 29) { throw "Los servicios no quedaron listos. Revisa .local-runtime/*.err.log." }
    }
}
