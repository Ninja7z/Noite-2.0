$ErrorActionPreference='Continue'
$log=Join-Path $PSScriptRoot '..\build\ssd_isolation_result.txt'
$log=[IO.Path]::GetFullPath($log)
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
Start-Transcript -Path $log -Force | Out-Null
$counterPaths=@(
'\PhysicalDisk(0 C:)\% tempo de disco',
'\PhysicalDisk(0 C:)\Média de disco s/transferência',
'\PhysicalDisk(0 C:)\Comprimento médio da fila de disco',
'\PhysicalDisk(0 C:)\Bytes de disco/s'
)
function SampleDisk($label) {
  Write-Output ''
  Write-Output ('=== '+$label+' ===')
  try {
    $samples=Get-Counter -Counter $counterPaths -SampleInterval 1 -MaxSamples 8
    foreach($s in $samples) {
      $vals=@()
      foreach($c in $s.CounterSamples) {
        $vals += ("{0}={1}" -f ($c.Path -replace '^.*\\',''),[math]::Round($c.CookedValue,3))
      }
      Write-Output ($s.Timestamp.ToString('HH:mm:ss')+' '+($vals -join ' | '))
    }
  } catch { Write-Output ('COUNTER_ERROR '+$_.Exception.Message) }
}
function TopIO($label) {
  Write-Output ''
  Write-Output ('=== '+$label+' ===')
  try {
    $items=Get-CimInstance Win32_PerfFormattedData_PerfProc_Process
    $items | Where-Object {$_.Name -notin @('_Total','Idle') -and $_.IODataBytesPersec -gt 0} |
      Sort-Object IODataBytesPersec -Descending |
      Select-Object -First 12 Name,IDProcess,IOReadBytesPersec,IOWriteBytesPersec,IODataBytesPersec |
      Format-Table -AutoSize | Out-String | Write-Output
  } catch { Write-Output ('PROCESS_IO_ERROR '+$_.Exception.Message) }
}
Write-Output ('ADMIN='+([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
SampleDisk 'BASELINE'
TopIO 'TOP IO BASELINE'
$before=@(Get-Service WSearch,SysMain | Where-Object {$_.Status -eq 'Running'} | Select-Object -ExpandProperty Name)
foreach($n in $before){try{Stop-Service -Name $n -Force -ErrorAction Stop; Write-Output "PAUSED $n"}catch{Write-Output "STOP_FAIL $n $($_.Exception.Message)"}}
Start-Sleep -Seconds 2
SampleDisk 'SEARCH_SYSMAIN_PAUSED'
TopIO 'TOP IO WHILE PAUSED'
foreach($n in $before){try{Start-Service -Name $n -ErrorAction Stop; Write-Output "RESTORED $n"}catch{Write-Output "START_FAIL $n $($_.Exception.Message)"}}
Write-Output ''
Write-Output '=== FINAL SERVICES ==='
Get-Service WSearch,SysMain | Select-Object Name,Status,StartType | Format-Table -AutoSize | Out-String | Write-Output
Stop-Transcript | Out-Null
