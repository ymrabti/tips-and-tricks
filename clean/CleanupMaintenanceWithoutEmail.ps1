# 1. Clean Temp folders
Write-Output "Cleaning temp folders..."
Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:LOCALAPPDATA\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue

# 2. Empty Recycle Bin
Write-Output "Emptying Recycle Bin..."
$shell = New-Object -ComObject Shell.Application
$recycleBin = $shell.NameSpace(0xA)
$recycleBin.Items() | ForEach-Object { $recycleBin.InvokeVerb("delete") }

# 3. Run Disk Cleanup silently for system files
Write-Output "Running Disk Cleanup for system files..."
Start-Process -FilePath "cleanmgr.exe" -ArgumentList "/sagerun:1" -Wait

# 4. Clear Windows Update cache
Write-Output "Clearing Windows Update cache..."
Stop-Service -Name wuauserv -Force
Remove-Item -Path "C:\Windows\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
Start-Service -Name wuauserv

# 5. Remove old Windows Update backups
Write-Output "Removing old Windows Update backups..."
dism.exe /online /Cleanup-Image /StartComponentCleanup /ResetBase

# 6. Optional: Clear thumbnail cache
Write-Output "Clearing thumbnail cache..."
Remove-Item -Path "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\thumbcache_*.db" -Force -ErrorAction SilentlyContinue

Write-Output "Maintenance complete!"
