$ErrorActionPreference = 'Continue'
$log = Join-Path $PSScriptRoot '..\build\ssd_admin_diagnostics.txt'
$log = [IO.Path]::GetFullPath($log)
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
Start-Transcript -Path $log -Force | Out-Null
function Section($s) { Write-Output ''; Write-Output "========== $s ==========" }
function DiskSample($label) {
  Section $label
  try {
    $c = Get-Counter -Counter @(
      '\PhysicalDisk(_Total)\% Disk Time',
      '\PhysicalDisk(_Total)\Avg. Disk sec/Transfer',
      '\PhysicalDisk(_Total)\Current Disk Queue Length',
      '\PhysicalDisk(_Total)\Disk Bytes/sec'
    ) -SampleInterval 1 -MaxSamples 6
    foreach ($s in $c) {
      foreach ($v in $s.CounterSamples) {
        [pscustomobject]@{Time=$s.Timestamp;Counter=$v.Path;Value=[math]::Round($v.CookedValue,4)} |
          Format-Table -AutoSize | Out-String | Write-Output
      }
    }
  } catch { "COUNTER_ERROR: $($_.Exception.Message)" | Write-Output }
}
Section 'PRIVILEGE'
whoami /all
Section 'DISK DEVICE'
try { Get-CimInstance Win32_DiskDrive | Select-Object Index,Model,Status,Size,InterfaceType,PNPDeviceID | Format-List | Out-String | Write-Output } catch { $_ | Out-String | Write-Output }
try { Get-PhysicalDisk | Select-Object FriendlyName,MediaType,HealthStatus,OperationalStatus,Size,UniqueId | Format-List | Out-String | Write-Output } catch { $_ | Out-String | Write-Output }
try { Get-PhysicalDisk | Get-StorageReliabilityCounter | Format-List * | Out-String | Write-Output } catch { $_ | Out-String | Write-Output }
try { Get-Volume -DriveLetter C | Format-List DriveLetter,FileSystem,HealthStatus,OperationalStatus,Size,SizeRemaining | Out-String | Write-Output } catch { $_ | Out-String | Write-Output }
Section 'SERVICE STATE BEFORE'
$svcNames = 'WSearch','SysMain','wuauserv','bits','DoSvc','TrustedInstaller'
$before = Get-CimInstance Win32_Service | Where-Object {$_.Name -in $svcNames} | Select-Object Name,State,StartMode,ProcessId
$before | Format-Table -AutoSize | Out-String | Write-Output
DiskSample 'BASELINE DISK LATENCY'
Section 'TOP PROCESS IO'
try {
  Get-Counter -Counter '\Process(*)\IO Read Bytes/sec','\Process(*)\IO Write Bytes/sec' -SampleInterval 1 -MaxSamples 5 |
    ForEach-Object {$_.CounterSamples} |
    Where-Object {$_.CookedValue -gt 0 -and $_.InstanceName -notin @('_total','idle')} |
    Sort-Object CookedValue -Descending |
    Select-Object -First 25 Path,@{n='BytesPerSec';e={[math]::Round($_.CookedValue)}} |
    Format-Table -AutoSize | Out-String | Write-Output
} catch { "PROCESS_COUNTER_ERROR: $($_.Exception.Message)" | Write-Output }
Section 'TEMPORARY SEARCH/SYSMAIN ISOLATION'
$wasRunning = @($before | Where-Object {$_.Name -in @('WSearch','SysMain') -and $_.State -eq 'Running'} | Select-Object -ExpandProperty Name)
foreach ($name in $wasRunning) {
  try { Stop-Service -Name $name -Force -ErrorAction Stop; "Stopped $name for diagnostic test." | Write-Output }
  catch { "Could not stop $name : $($_.Exception.Message)" | Write-Output }
}
Start-Sleep -Seconds 12
DiskSample 'AFTER PAUSING SEARCH AND SYSMAIN'
foreach ($name in $wasRunning) {
  try { Start-Service -Name $name -ErrorAction Stop; "Restored $name." | Write-Output }
  catch { "Could not restore $name : $($_.Exception.Message)" | Write-Output }
}
Section 'NTFS ONLINE SCAN'
try {
  $p = Start-Process -FilePath "$env:SystemRoot\System32\chkdsk.exe" -ArgumentList 'C: /scan' -NoNewWindow -Wait -PassThru -RedirectStandardOutput (Join-Path $env:TEMP 'noite_chkdsk_scan.txt') -RedirectStandardError (Join-Path $env:TEMP 'noite_chkdsk_scan_err.txt')
  "CHKDSK_EXIT_CODE=$($p.ExitCode)" | Write-Output
  Get-Content (Join-Path $env:TEMP 'noite_chkdsk_scan.txt') -ErrorAction SilentlyContinue | Write-Output
  Get-Content (Join-Path $env:TEMP 'noite_chkdsk_scan_err.txt') -ErrorAction SilentlyContinue | Write-Output
} catch { "CHKDSK_ERROR: $($_.Exception.Message)" | Write-Output }
Section 'STORAGE EVENTS LAST 7 DAYS'
try {
  Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 3000 |
    Where-Object {$_.ProviderName -match 'disk|ntfs|storahci|storport|storage' -and $_.Level -in 1,2,3} |
    Select-Object -First 40 TimeCreated,ProviderName,Id,LevelDisplayName,Message |
    Format-List | Out-String | Write-Output
} catch { "EVENT_ERROR: $($_.Exception.Message)" | Write-Output }
Section 'FINAL SERVICE STATE'
Get-Service -Name $svcNames | Select-Object Name,Status,StartType | Format-Table -AutoSize | Out-String | Write-Output
Stop-Transcript | Out-Null
