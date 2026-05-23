#!/usr/bin/env pwsh
# Windows equivalent of start.sh
Set-Location $PSScriptRoot

# Load .env if present
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

$port = 8080
if (Test-Path config.json) {
    try {
        $cfg = Get-Content config.json -Raw | ConvertFrom-Json
        if ($cfg.port) { $port = $cfg.port }
    } catch {}
}

Write-Host "[>] Starting server on port $port..." -ForegroundColor Cyan
$serverJob = Start-Job -ScriptBlock {
    param($p)
    Set-Location $using:PSScriptRoot
    & py -m uvicorn server:app --host 0.0.0.0 --port $p --reload
} -ArgumentList $port

try {
    Start-Sleep -Seconds 2

    $cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cloudflared) {
        Write-Host "[>] Starting Cloudflare Tunnel..." -ForegroundColor Cyan
        & cloudflared tunnel --url "http://localhost:$port"
    } else {
        Write-Host "[!] cloudflared not installed. LAN only: http://localhost:$port" -ForegroundColor Yellow
        Write-Host "    For public access: winget install --id Cloudflare.cloudflared" -ForegroundColor Yellow
        Write-Host "    Press Ctrl+C to stop." -ForegroundColor Cyan
        Wait-Job $serverJob | Out-Null
    }
} finally {
    Write-Host "[x] Shutting down..." -ForegroundColor Cyan
    Stop-Job $serverJob -ErrorAction SilentlyContinue
    Remove-Job $serverJob -Force -ErrorAction SilentlyContinue
}
