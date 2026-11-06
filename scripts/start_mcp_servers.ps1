[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$NoiteRoot = (Resolve-Path (Join-Path $ProjectRoot "..\..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDirectory = Join-Path $NoiteRoot "Temporarios\Logs\MCP"
$Port = 8767

if (-not (Test-Path $Python)) { throw "Python do projeto n?o encontrado: $Python" }
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

function Get-PortOwner([int]$Port) {
    try {
        return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
            Select-Object -First 1 -ExpandProperty OwningProcess
    } catch { return $null }
}

$owner = Get-PortOwner $Port
if ($owner) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$owner" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -match 'noite\.mcp_server') {
        Write-Host "Noite MCP j? est? ativo na porta $Port (PID $owner)."
        exit 0
    }
    throw "A porta $Port est? ocupada por outro processo (PID $owner); n?o vou iniciar uma duplicata."
}

$stdout = Join-Path $LogDirectory "noite-mcp.out.log"
$stderr = Join-Path $LogDirectory "noite-mcp.err.log"
$process = Start-Process -FilePath $Python -ArgumentList @("-m", "noite.mcp_server") -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Write-Host "Iniciado Noite MCP (PID $($process.Id)); aguardando porta $Port..."

$ready = $false
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    $owner = Get-PortOwner $Port
    if ($owner) {
        $ready = $true
        break
    }
    if ($process.HasExited) { break }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    $detail = if (Test-Path $stderr) { Get-Content $stderr -Tail 30 } else { "sem log de erro" }
    throw "Noite MCP n?o iniciou na porta $Port. $detail"
}
Write-Host "OK: Noite MCP em http://127.0.0.1:$Port/mcp"
Write-Host "Roblox MCP n?o foi iniciado: configura??o/proxy ainda n?o foi restaurado."
