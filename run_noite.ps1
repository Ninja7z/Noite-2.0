[CmdletBinding()]
param(
    [switch]$Status,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$NoiteRoot = (Resolve-Path (Join-Path $ProjectRoot "..\..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ApiDirectory = Join-Path $ProjectRoot "integrations\openwebui"
$LogDirectory = Join-Path $NoiteRoot "Temporarios\Logs\NoiteAPI"
$StateDirectory = Join-Path $NoiteRoot "Permanentes\Dados\NoiteAPI"
$StateFile = Join-Path $StateDirectory "run_noite-processes.json"
$env:PYTHONPATH = "$(Join-Path $ProjectRoot 'src');$ApiDirectory;$env:PYTHONPATH"

$Services = @(
    @{ Name = "Noite Web"; Port = 8766; Args = @("-m", "uvicorn", "noite_api:app", "--host", "0.0.0.0", "--port", "8766"); Cwd = $ApiDirectory }
)
$StatusServices = @(
    @{ Name = "OpenWebUI API"; Port = 8765 },
    @{ Name = "Noite Web"; Port = 8766 },
    @{ Name = "Noite MCP"; Port = 8767 },
    @{ Name = "Roblox MCP"; Port = 8768 },
    @{ Name = "Open WebUI"; Port = 8080 },
    @{ Name = "Ollama"; Port = 11434 }
)
$McpLauncher = Join-Path $ProjectRoot "scripts\start_mcp_servers.ps1"
$OpenWebUiLauncher = Join-Path $ApiDirectory "Start-Noite-OpenWebUI.ps1"

function Test-LocalPort([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Port)
        if (-not $task.Wait(350)) { return $false }
        return $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Get-ServiceStatus($Service) {
    if (Test-LocalPort $Service.Port) {
        return "porta $($Service.Port) responde (processo preexistente ou ativo)"
    }
    return "porta $($Service.Port) indisponível"
}

if (-not (Test-Path $Python)) {
    throw "Python do ambiente virtual não encontrado: $Python"
}
if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    throw "Arquivo .env não encontrado. Configure as chaves localmente antes de iniciar."
}
if (-not (Test-Path $McpLauncher)) { throw "Inicializador MCP não encontrado: $McpLauncher" }
if (-not (Test-Path $OpenWebUiLauncher)) { throw "Inicializador Open WebUI não encontrado: $OpenWebUiLauncher" }
New-Item -ItemType Directory -Path $LogDirectory, $StateDirectory -Force | Out-Null

if ($Status) {
    foreach ($service in $StatusServices) {
        "{0}: {1}" -f $service.Name, (Get-ServiceStatus $service)
    }
    exit 0
}

# O servidor MCP recusa iniciar sem token. Apenas verificamos presença, sem exibir valor.
$envText = Get-Content -Raw (Join-Path $ProjectRoot ".env")
if ($envText -notmatch '(?m)^\s*NOITE_MCP_AUTH_TOKEN\s*=\s*[^\s#]+') {
    throw "NOITE_MCP_AUTH_TOKEN está ausente ou vazio no .env. O segredo não será exibido."
}

$started = @()
foreach ($service in $Services) {
    if (Test-LocalPort $service.Port) {
        Write-Host ("{0}: porta {1} já está respondendo; não vou iniciar duplicata." -f $service.Name, $service.Port)
        continue
    }

    $stdout = Join-Path $LogDirectory ("{0}.out.log" -f $service.Port)
    $stderr = Join-Path $LogDirectory ("{0}.err.log" -f $service.Port)
    $process = Start-Process -FilePath $Python -ArgumentList $service.Args -WorkingDirectory $service.Cwd -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

    $started += [pscustomobject]@{
        Name = $service.Name
        Port = $service.Port
        PID = $process.Id
        StartedAt = (Get-Date).ToString("o")
    }
    Write-Host ("Iniciado {0} (PID {1}); verificando porta {2}..." -f $service.Name, $process.Id, $service.Port)
}

# Guarda somente os processos iniciados nesta execução. Não encerra processos por nome/porta.
if ($started.Count -gt 0) {
    $started | ConvertTo-Json -Depth 3 | Set-Content -Encoding UTF8 $StateFile
}

foreach ($service in $Services) {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (Test-LocalPort $service.Port) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 400
    }
    if ($ready) {
        Write-Host ("OK: {0} em http://127.0.0.1:{1}" -f $service.Name, $service.Port)
    } else {
        Write-Warning ("{0} não respondeu na porta {1}. Consulte os logs em {2}" -f $service.Name, $service.Port, $LogDirectory)
    }
}

# Inicializa as duas pontes MCP já registradas no Open WebUI, sem abrir interfaces.
if (-not (Test-Path $McpLauncher)) { throw "Inicializador MCP não encontrado: $McpLauncher" }
& $McpLauncher
if (-not $?) { throw "Falha ao iniciar as pontes MCP." }

# Inicia a API OpenAI-compatible da Noite e o Open WebUI, sem abrir o navegador.
& $OpenWebUiLauncher -NoBrowser
if (-not $?) { throw "Falha ao iniciar a integração Open WebUI." }

Write-Host "Servidores verificados. Mascote não iniciado; continua independente e usa Alt+C."
Write-Host "Noite Web: http://127.0.0.1:8766/"
Write-Host "Open WebUI: http://127.0.0.1:8080/"
Write-Host "MCP Noite: 127.0.0.1:8767 | MCP Roblox: pending restoration (8768)"
if ($NoBrowser) { Write-Host "Modo sem navegador solicitado; nenhum app visual foi aberto." }
