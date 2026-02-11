Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* |
Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |
Where-Object { $_.DisplayName } |
Sort-Object DisplayName |
Export-Csv "$env:USERPROFILE\Desktop\InstalledPrograms.csv" -NoTypeInformation
Write-Host "Installed programs have been exported to InstalledPrograms.csv on your Desktop."

$paths = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

Get-ItemProperty $paths |
Select DisplayName, DisplayVersion, Publisher, InstallDate |
Where { $_.DisplayName } |
Sort DisplayName |
Export-Csv "$env:USERPROFILE\Desktop\InstalledApps_FULL.csv" -NoTypeInformation


Write-Host "Full list of installed applications has been exported to InstalledApps_FULL.csv on your Desktop."

Get-AppxPackage |
Select Name, Version, Publisher |
Export-Csv "$env:USERPROFILE\Desktop\StoreApps.csv" -NoTypeInformation

Write-Host "Installed Store apps have been exported to StoreApps.csv on your Desktop."

