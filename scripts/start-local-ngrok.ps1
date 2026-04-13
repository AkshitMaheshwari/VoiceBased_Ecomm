param(
    [int]$Port = 8000,
    [string]$HostName = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$ngrokLocal = Join-Path $repoRoot "tools\ngrok.exe"
$ngrok = if (Test-Path $ngrokLocal) {
    $ngrokLocal
} else {
    (Get-Command ngrok -ErrorAction SilentlyContinue).Source
}

if (-not $ngrok) {
    throw "ngrok was not found. Put ngrok.exe in tools\ngrok.exe or add ngrok to PATH."
}

$python = Join-Path $repoRoot "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}

if (-not $python) {
    throw "Python was not found. Activate the project venv or install Python."
}

$logsDir = Join-Path $repoRoot "tools"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$ngrokApi = "http://127.0.0.1:4040/api/tunnels"
$ngrokRunning = Get-Process ngrok -ErrorAction SilentlyContinue
if (-not $ngrokRunning) {
    Start-Process -FilePath $ngrok `
        -ArgumentList @("http", "$Port", "--log", "stdout") `
        -RedirectStandardOutput (Join-Path $logsDir "ngrok.log") `
        -RedirectStandardError (Join-Path $logsDir "ngrok.err.log") `
        -WindowStyle Hidden
}

$publicUrl = $null
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $tunnels = Invoke-RestMethod -Uri $ngrokApi -TimeoutSec 3
        $publicUrl = ($tunnels.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1).public_url
        if ($publicUrl) {
            break
        }
    } catch {
        # ngrok API may take a moment to come up.
    }
}

if (-not $publicUrl) {
    $log = Join-Path $logsDir "ngrok.log"
    if (Test-Path $log) {
        Get-Content $log -Tail 40 | ForEach-Object {
            $_ -replace "Your authtoken: .*", "Your authtoken: ***"
        }
    }
    throw "ngrok did not publish an HTTPS tunnel. Check the ngrok authtoken with: tools\ngrok.exe config add-authtoken <your-token>"
}

$envFile = Join-Path $repoRoot ".env"
if (Test-Path $envFile) {
    $envText = Get-Content $envFile -Raw
    if ($envText -match "(?m)^PUBLIC_BASE_URL=") {
        $envText = $envText -replace "(?m)^PUBLIC_BASE_URL=.*$", "PUBLIC_BASE_URL=$publicUrl"
    } else {
        $envText = $envText.TrimEnd() + "`r`nPUBLIC_BASE_URL=$publicUrl`r`n"
    }
    Set-Content -Path $envFile -Value $envText -NoNewline
} else {
    Set-Content -Path $envFile -Value "PUBLIC_BASE_URL=$publicUrl`r`n"
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $listener) {
    $appPath = Join-Path $repoRoot "app.py"
    Start-Process -FilePath $python `
        -ArgumentList @("`"$appPath`"") `
        -WorkingDirectory $repoRoot `
        -RedirectStandardOutput (Join-Path $logsDir "app.log") `
        -RedirectStandardError (Join-Path $logsDir "app.err.log") `
        -WindowStyle Hidden
}

$health = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $health = Invoke-RestMethod -Uri "http://$HostName`:$Port/api/health" -TimeoutSec 3
        break
    } catch {
        # FastAPI is still starting.
    }
}

if (-not $health) {
    throw "FastAPI did not become healthy on http://$HostName`:$Port. Check tools\app.err.log."
}

[pscustomobject]@{
    LocalUrl = "http://$HostName`:$Port"
    PublicUrl = $publicUrl
    VoiceWebhook = "$publicUrl/webhooks/voice/incoming"
    Health = $health
} | Format-List
