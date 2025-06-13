# --- Config ---
$logPath = "C:\Scripts\CleanupLog.txt"

# Ensure the folder exists
if (!(Test-Path -Path (Split-Path $logPath))) {
    New-Item -Path (Split-Path $logPath) -ItemType Directory -Force | Out-Null
}
$smtpServer = "smtp.mail.me.com"
$smtpPort = 587
$smtpUser = ""
$smtpPass = ""
$emailTo = ""
$emailFrom = ""
$emailSubject = "Windows Cleanup Task Report"

# --- Logging helper ---
function Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "$timestamp - $message"
    Write-Output $entry
    Add-Content -Path $logPath -Value $entry
}

try {
    Log "Cleanup started."

    # Clean Temp folders
    Log "Cleaning temp folders..."
    Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$env:LOCALAPPDATA\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue

    # Empty Recycle Bin
    Log "Emptying Recycle Bin..."
    $shell = New-Object -ComObject Shell.Application
    $recycleBin = $shell.NameSpace(0xA)
    $recycleBin.Items() | ForEach-Object { $recycleBin.InvokeVerb("delete") }

    # Disk Cleanup for system files
    Log "Running Disk Cleanup for system files..."
    Start-Process -FilePath "cleanmgr.exe" -ArgumentList "/sagerun:1" -Wait

    # Clear Windows Update cache
    Log "Clearing Windows Update cache..."
    Stop-Service -Name wuauserv -Force
    Remove-Item -Path "C:\Windows\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
    Start-Service -Name wuauserv

    # Remove old Windows Update backups
    Log "Removing old Windows Update backups..."
    dism.exe /online /Cleanup-Image /StartComponentCleanup /ResetBase | Out-Null

    # Clear thumbnail cache
    Log "Clearing thumbnail cache..."
    Remove-Item -Path "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\thumbcache_*.db" -Force -ErrorAction SilentlyContinue

    Log "Cleanup completed successfully."

    # Send email notification with log
    Log "Sending email notification..."
    $body = Get-Content -Path $logPath | Out-String
    $message = New-Object System.Net.Mail.MailMessage $emailFrom, $emailTo, $emailSubject, $body
    $smtp = New-Object System.Net.Mail.SmtpClient $smtpServer, $smtpPort
    $smtp.EnableSsl = $true
    $smtp.Credentials = New-Object System.Net.NetworkCredential($smtpUser, $smtpPass)
    $smtp.Send($message)
    Log "Email sent."

}
catch {
    Log "ERROR: $_"
}
