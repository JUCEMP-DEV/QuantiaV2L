$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$backendEnv = Join-Path $projectRoot "Backend\.env.local"
$frontendEnv = Join-Path $projectRoot "Frontend\.env.local"

function Convert-SecretToText([Security.SecureString]$secret) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

$supabaseUrl = (Read-Host "Project URL de Supabase (Connect o Settings > API Keys)").Trim().Trim('"').Trim("'").TrimEnd('/')
$serviceRoleKey = (Convert-SecretToText (Read-Host "Legacy service_role API key (JWT; no es la DB password)" -AsSecureString)).Trim().Trim('"').Trim("'")
$anonKey = (Convert-SecretToText (Read-Host "Legacy anon API key del mismo proyecto" -AsSecureString)).Trim().Trim('"').Trim("'")

if ($supabaseUrl -notmatch '^https://.+\.supabase\.co$') {
    throw "SUPABASE_URL no tiene el formato esperado https://<proyecto>.supabase.co"
}
if ([string]::IsNullOrWhiteSpace($serviceRoleKey) -or [string]::IsNullOrWhiteSpace($anonKey)) {
    throw "Las claves de Supabase son obligatorias."
}
if ($serviceRoleKey -notmatch '^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$') {
    throw "La service_role debe ser la clave JWT legacy que empieza con eyJ; no introduzcas la DB password."
}
if ($anonKey -notmatch '^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$') {
    throw "La anon key debe ser la clave JWT legacy que empieza con eyJ."
}

function Test-SupabaseApiKey([string]$url, [string]$key, [string]$label) {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "$url/auth/v1/settings" `
            -Headers @{ apikey = $key; Authorization = "Bearer $key" } -TimeoutSec 20 | Out-Null
    }
    catch {
        throw "$label no fue aceptada por la Project URL indicada. Comprueba que URL y claves pertenezcan al mismo proyecto."
    }
}

Test-SupabaseApiKey $supabaseUrl $serviceRoleKey "La service_role key"
Test-SupabaseApiKey $supabaseUrl $anonKey "La anon key"

$secretBytes = New-Object byte[] 48
$randomGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $randomGenerator.GetBytes($secretBytes)
}
finally {
    $randomGenerator.Dispose()
}
$authSecret = [Convert]::ToBase64String($secretBytes)
$tessdataDir = (Join-Path $projectRoot "Backend\.local-tools\tessdata").Replace('\', '/')

$backendLines = @(
    "SUPABASE_URL=$supabaseUrl",
    "SUPABASE_SERVICE_ROLE_KEY=$serviceRoleKey",
    "DOCUMENT_PERSISTENCE_BACKEND=supabase",
    "DOCUMENT_TABLE_NAME=documents",
    "DOCUMENT_STORAGE_BUCKET=quantia-documents",
    "VECTOR_STORE_BACKEND=supabase",
    "VECTOR_TABLE_NAME=document_chunks",
    "EMBEDDING_BACKEND=hashing",
    "EMBEDDING_MODEL=hashing-384",
    "EMBEDDING_DIMENSION=384",
    "RAG_CHUNK_SIZE=150",
    "RAG_CHUNK_OVERLAP=30",
    "RAG_TOP_K=3",
    "OLLAMA_HOST=http://127.0.0.1:11434",
    "OLLAMA_MODEL=llama3.2:3b",
    "OLLAMA_CONTEXT_LENGTH=2048",
    "OLLAMA_MAX_TOKENS=64",
    "OLLAMA_TIMEOUT_SECONDS=60",
    "OLLAMA_TEMPERATURE=0",
    "OCR_ENGINE=tesseract",
    "TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe",
    "TESSERACT_LANGUAGE=spa",
    "TESSERACT_DATA_DIR=$tessdataDir",
    "POPPLER_PATH=C:/Users/yungu/AppData/Local/Microsoft/WinGet/Packages/oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe/poppler-25.07.0/Library/bin",
    "AUTH_TOKEN_SECRET=$authSecret",
    "AUTH_TOKEN_TTL_SECONDS=28800",
    'BACKEND_CORS_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]',
    "BACKEND_CORS_ORIGIN_REGEX="
)
$frontendLines = @(
    "VITE_BACKEND_URL=http://127.0.0.1:8000",
    "VITE_SUPABASE_URL=$supabaseUrl",
    "VITE_SUPABASE_ANON_KEY=$anonKey"
)

[IO.File]::WriteAllLines($backendEnv, $backendLines, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllLines($frontendEnv, $frontendLines, [Text.UTF8Encoding]::new($false))

$serviceRoleKey = $null
$anonKey = $null
$authSecret = $null
Write-Output "Configuracion local creada. Las claves quedaron solo en archivos ignorados por Git."
