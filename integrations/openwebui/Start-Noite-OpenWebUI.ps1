[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\crist\Noite-2.0-worktrees\stabilize-core-lab-1d2bbe70186b491093ebdb2b7307e001"
$ApiHome = Join-Path $env:LOCALAPPDATA "NoiteAPI"
$WebHome = Join-Path $env:LOCALAPPDATA "OpenWebUI"
$ApiPython = Join-Path $ApiHome "venv\Scripts\python.exe"
$WebCli = Join-Path $WebHome "venv\Scripts\open-webui.exe"
$ApiScript = Join-Path $ProjectRoot "integrations\openwebui\noite_api.py"
$KeyFile = Join-Path $ApiHome "openwebui_api_key.txt"
$LogDir = Join-Path $ApiHome "logs"
$WebData = Join-Path $WebHome "data"

New-Item -ItemType Directory -Force -Path $LogDir, $WebData | Out-Null

foreach ($required in @($ApiPython, $WebCli, $ApiScript)) {
    if (-not (Test-Path $required)) {
        throw "Arquivo necessário não encontrado: $required"
    }
}

if (-not (Test-Path $KeyFile)) {
    $bytes = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $key = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    [System.IO.File]::WriteAllText($KeyFile, $key)
}
$ApiKey = (Get-Content -Raw $KeyFile).Trim()
if ($ApiKey.Length -lt 40) { throw "A chave local da API da Noite está inválida." }

function Test-LocalPort([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $result = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(300)
        if (-not $success) { return $false }
        $client.EndConnect($result)
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Test-NoiteApiReady {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 3
        if ($health.status -ne "ok" -or $health.service -ne "Noite 2.0") { return $false }
        $headers = @{ Authorization = "Bearer $ApiKey" }
        $models = Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/models" -Headers $headers -TimeoutSec 3
        return $models.object -eq "list" -and @($models.data | Where-Object { $_.id -eq "noite-2.0" }).Count -gt 0
    } catch {
        return $false
    }
}

function Test-OpenWebUiReady {
    try {
        $health = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -TimeoutSec 3
        return [int]$health.StatusCode -eq 200
    } catch {
        return $false
    }
}

# 1) API compatível com OpenAI, ligada ao AssistantService e ao SQLite da Noite.
if (Test-LocalPort 8765) {
    if (-not (Test-NoiteApiReady)) {
        throw "A porta 8765 já está ocupada por outro serviço. A Noite não vai reutilizá-la."
    }
} else {
    $env:NOITE_OPENWEBUI_API_KEY = $ApiKey
    $ApiOut = Join-Path $LogDir "api.out.log"
    $ApiErr = Join-Path $LogDir "api.err.log"
    Start-Process -FilePath $ApiPython -ArgumentList @($ApiScript) -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr | Out-Null
}

$apiReady = $false
for ($i = 0; $i -lt 60; $i++) {
    if (Test-NoiteApiReady) { $apiReady = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $apiReady) { throw "A API da Noite não iniciou ou não passou no health check. Consulte $LogDir." }

# 2) Open WebUI: somente localhost, persistência própria e modelo Noite pré-configurado.
$env:DATA_DIR = $WebData
$env:OPENAI_API_BASE_URLS = "http://127.0.0.1:8765/v1"
$env:OPENAI_API_KEYS = $ApiKey
# Mostra os modelos locais do Ollama junto ao adaptador da Noite.
$env:ENABLE_OLLAMA_API = "true"
$env:ENABLE_OPENAI_API = "true"
$env:ENABLE_PIP_INSTALL_FRONTMATTER_REQUIREMENTS = "false"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:WEBUI_NAME = "Noite"
$env:WEBUI_AUTH = "true"

if (Test-LocalPort 8080) {
    if (-not (Test-OpenWebUiReady)) {
        throw "A porta 8080 já está ocupada por outro serviço. O Open WebUI não será iniciado sobre ela."
    }
} else {
    $WebOut = Join-Path $WebHome "openwebui.out.log"
    $WebErr = Join-Path $WebHome "openwebui.err.log"
    Start-Process -FilePath $WebCli -ArgumentList @("serve", "--host", "127.0.0.1", "--port", "8080") -WorkingDirectory $WebHome -WindowStyle Hidden -RedirectStandardOutput $WebOut -RedirectStandardError $WebErr | Out-Null
}

$webReady = $false
for ($i = 0; $i -lt 120; $i++) {
    if (Test-OpenWebUiReady) { $webReady = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $webReady) { throw "O Open WebUI não iniciou ou não passou no health check. Consulte $WebHome." }

# 3) A abertura do navegador é opcional. O modo padrão integrado inicia apenas serviços.
if (-not $NoBrowser) {
    $Edge = Get-Command "msedge.exe" -ErrorAction SilentlyContinue
    $EdgePath = if ($Edge) { $Edge.Source } else { $null }
    if (-not $EdgePath) {
        $candidates = @(
            (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe")
        )
        $EdgePath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if (-not $EdgePath) { throw "Microsoft Edge não foi encontrado." }
    Start-Process -FilePath $EdgePath -ArgumentList @("--app=http://127.0.0.1:8080") | Out-Null
} else {
    Write-Output "Open WebUI ativo em http://127.0.0.1:8080 (navegador não aberto)."
}
