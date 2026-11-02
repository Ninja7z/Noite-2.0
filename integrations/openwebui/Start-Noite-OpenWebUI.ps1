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

# 1) API compatível com OpenAI, ligada ao AssistantService e ao SQLite da Noite.
if (-not (Test-LocalPort 8765)) {
    $env:NOITE_OPENWEBUI_API_KEY = $ApiKey
    $ApiOut = Join-Path $LogDir "api.out.log"
    $ApiErr = Join-Path $LogDir "api.err.log"
    Start-Process -FilePath $ApiPython -ArgumentList @($ApiScript) -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr | Out-Null
}

$apiReady = $false
for ($i = 0; $i -lt 60; $i++) {
    if (Test-LocalPort 8765) { $apiReady = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $apiReady) { throw "A API da Noite não iniciou. Consulte $LogDir." }

# 2) Open WebUI: somente localhost, persistência própria e modelo Noite pré-configurado.
$env:DATA_DIR = $WebData
$env:OPENAI_API_BASE_URLS = "http://127.0.0.1:8765/v1"
$env:OPENAI_API_KEYS = $ApiKey
# Mostra os modelos locais do Ollama junto ao adaptador da Noite.
$env:ENABLE_OLLAMA_API = "true"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:WEBUI_NAME = "Noite"
$env:ENABLE_FORWARD_USER_INFO_HEADERS = "true"

if (-not (Test-LocalPort 8080)) {
    $WebOut = Join-Path $WebHome "openwebui.out.log"
    $WebErr = Join-Path $WebHome "openwebui.err.log"
    Start-Process -FilePath $WebCli -ArgumentList @("serve", "--host", "127.0.0.1", "--port", "8080") -WorkingDirectory $WebHome -WindowStyle Hidden -RedirectStandardOutput $WebOut -RedirectStandardError $WebErr | Out-Null
}

$webReady = $false
for ($i = 0; $i -lt 120; $i++) {
    if (Test-LocalPort 8080) { $webReady = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $webReady) { throw "O Open WebUI não iniciou. Consulte $WebHome." }

# 3) Abre a interface como aplicativo do Edge.
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
