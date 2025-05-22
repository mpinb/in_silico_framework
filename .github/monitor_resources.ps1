# monitor_resources.ps1
# Logs CPU and RAM usage to a file every 5 seconds.

param (
    [string]$LogFile = "./tests/logs/resource_usage.log",
    [int]$Interval = 5
)

# Ensure the log file exists
New-Item -ItemType File -Force -Path $LogFile | Out-Null

# Start monitoring
Write-Host "Starting resource monitoring..."
while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $cpu = (Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples.CookedValue
    $ram = (Get-Counter '\Memory\Available MBytes').CounterSamples.CookedValue
    $totalRam = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1MB
    $usedRam = $totalRam - $ram

    # Log the data
    "$timestamp, CPU: $([math]::Round($cpu, 2))%, RAM Used: $([math]::Round($usedRam, 2)) MB, RAM Total: $([math]::Round($totalRam, 2)) MB" | Out-File -Append -FilePath $LogFile

    Start-Sleep -Seconds $Interval
}