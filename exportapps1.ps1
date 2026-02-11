# Create export folder
$exportPath = "$env:USERPROFILE\Desktop\Windows_Full_Inventory"
New-Item -ItemType Directory -Force -Path $exportPath | Out-Null

Write-Host "Exporting Windows Inventory..." -ForegroundColor Cyan

# =============================
# 1. Installed Win32 Programs
# =============================
$regPaths = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

Get-ItemProperty $regPaths |
Where-Object { $_.DisplayName } |
Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |
Sort-Object DisplayName |
Export-Csv "$exportPath\Installed_Programs.csv" -NoTypeInformation

# =============================
# 2. Microsoft Store Apps
# =============================
Get-AppxPackage |
Select Name, Version, Publisher |
Export-Csv "$exportPath\Store_Apps.csv" -NoTypeInformation

# =============================
# 3. Windows Optional Features
# =============================
Get-WindowsOptionalFeature -Online |
Select FeatureName, State |
Export-Csv "$exportPath\Windows_Features.csv" -NoTypeInformation

# =============================
# 4. Installed Drivers
# =============================
Get-WindowsDriver -Online |
Select Driver, ClassName, ProviderName, Version, Date |
Export-Csv "$exportPath\Drivers.csv" -NoTypeInformation

# =============================
# 5. Winget Packages (if installed)
# =============================
if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget list --source winget |
    Out-File "$exportPath\Winget_List.txt"
}

# =============================
# 6. Installed Windows Updates
# =============================
Get-HotFix |
Select HotFixID, Description, InstalledOn |
Export-Csv "$exportPath\Windows_Updates.csv" -NoTypeInformation

Write-Host "DONE! Inventory saved to:" -ForegroundColor Green
Write-Host $exportPath -ForegroundColor Yellow
