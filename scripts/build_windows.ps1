param(
    [string]$Python = ".venv\Scripts\python.exe",
    [switch]$CopyToDesktop
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonPath = if ([System.IO.Path]::IsPathRooted($Python)) { $Python } else { Join-Path $Root $Python }
if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python do ambiente virtual não encontrado: $PythonPath. Instale as dependências desktop e build."
}

Push-Location $Root
try {
    $BuildDir = Join-Path $Root "build\launcher"
    New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null
    $ConfigModule = Join-Path $BuildDir "noite_path_placeholder.py"
    $PythonRoot = $Root.Replace("\", "\\")
    Set-Content -LiteralPath $ConfigModule -Value "PROJECT_ROOT = r'$PythonRoot'" -Encoding utf8
    $Source = Join-Path $Root "packaging\noite_bootstrap.py"
    $Dist = Join-Path $Root "dist"
    $Work = Join-Path $Root "build\pyinstaller"
    & $PythonPath -m PyInstaller --noconfirm --onefile --windowed --clean --name Noite --paths $BuildDir --specpath $BuildDir --distpath $Dist --workpath $Work $Source
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller terminou com código $LASTEXITCODE." }
    $Exe = Join-Path $Root "dist\Noite.exe"
    if (-not (Test-Path -LiteralPath $Exe)) { throw "Artefato não encontrado: $Exe" }
    if ($CopyToDesktop) {
        $Desktop = [Environment]::GetFolderPath("Desktop")
        Copy-Item -LiteralPath $Exe -Destination (Join-Path $Desktop "Noite.exe") -Force
        Write-Output "Executável copiado para $(Join-Path $Desktop 'Noite.exe')"
    } else {
        Write-Output "Executável criado em $Exe"
    }
} finally {
    Pop-Location
}
