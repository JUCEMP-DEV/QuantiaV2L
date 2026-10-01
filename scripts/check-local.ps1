$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$backendEnv = Join-Path $projectRoot "Backend\.env.local"
$frontendEnv = Join-Path $projectRoot "Frontend\.env.local"
$requiredBackend = @(
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "AUTH_TOKEN_SECRET",
    "DOCUMENT_PERSISTENCE_BACKEND",
    "VECTOR_STORE_BACKEND",
    "OLLAMA_HOST",
    "OLLAMA_MODEL"
)
$requiredFrontend = @("VITE_BACKEND_URL", "VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY")

function Read-EnvMap([string]$path) {
    $values = @{}
    if (-not (Test-Path -LiteralPath $path)) {
        return $values
    }
    foreach ($line in Get-Content -LiteralPath $path) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            $values[$matches[1]] = $matches[2].Trim().Trim('"')
        }
    }
    return $values
}

function Test-Configured([hashtable]$map, [string[]]$keys) {
    foreach ($key in $keys) {
        $value = [string]$map[$key]
        $ready = -not [string]::IsNullOrWhiteSpace($value) -and $value -notmatch 'REEMPLAZAR|TU_PROYECTO'
        [pscustomobject]@{ Component = "env"; Check = $key; Ready = $ready }
    }
}

$backendValues = Read-EnvMap $backendEnv
$frontendValues = Read-EnvMap $frontendEnv
$results = @()
$results += Test-Configured $backendValues $requiredBackend
$results += Test-Configured $frontendValues $requiredFrontend

$ollamaReady = $false
$modelReady = $false
try {
    $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3
    $ollamaReady = $true
    $modelReady = @($tags.models | ForEach-Object { $_.name }) -contains "llama3.2:3b"
}
catch {}
$results += [pscustomobject]@{ Component = "ollama"; Check = "API local"; Ready = $ollamaReady }
$results += [pscustomobject]@{ Component = "ollama"; Check = "llama3.2:3b"; Ready = $modelReady }

$tesseractPath = [string]$backendValues["TESSERACT_CMD"]
$popplerPath = [string]$backendValues["POPPLER_PATH"]
$results += [pscustomobject]@{ Component = "ocr"; Check = "Tesseract"; Ready = (Test-Path -LiteralPath $tesseractPath -PathType Leaf) }
$results += [pscustomobject]@{ Component = "ocr"; Check = "Poppler"; Ready = (Test-Path -LiteralPath (Join-Path $popplerPath "pdftoppm.exe") -PathType Leaf) }

foreach ($service in @(
    @{ Component = "backend"; Uri = "http://127.0.0.1:8000/health" },
    @{ Component = "frontend"; Uri = "http://127.0.0.1:5173" }
)) {
    $ready = $false
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $service.Uri -TimeoutSec 3
        $ready = $response.StatusCode -eq 200
    }
    catch {}
    $results += [pscustomobject]@{ Component = $service.Component; Check = $service.Uri; Ready = $ready }
}

$results | Format-Table -AutoSize
if ($results.Ready -contains $false) {
    exit 1
}
