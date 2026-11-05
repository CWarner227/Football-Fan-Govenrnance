$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Install and start Docker Desktop, then launch this file again.'
    }
    $engineType = docker info --format '{{.OSType}}'
    if ($LASTEXITCODE -ne 0 -or $engineType -ne 'linux') {
        throw 'Start Docker Desktop with Linux containers, then launch this file again.'
    }
    docker compose --project-directory $projectRoot -f (Join-Path $projectRoot 'compose.yaml') up --build --detach --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) {
        throw 'Dashboard startup failed. Check the Docker output above. Port 8000 must be free.'
    }
    Write-Host 'Dashboard ready at http://localhost:8000'
    Start-Process 'http://localhost:8000'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
