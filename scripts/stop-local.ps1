$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$runtimeDir = Join-Path $projectRoot ".local-runtime"

foreach ($name in @("frontend", "backend", "ollama")) {
    $pidFile = Join-Path $runtimeDir "$name.pid"
    if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) {
        continue
    }
    $processId = [int](Get-Content -LiteralPath $pidFile -Raw)
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $processId
        Write-Output "Detenido: $name (PID $processId)"
    }
    Remove-Item -LiteralPath $pidFile -Force
}
