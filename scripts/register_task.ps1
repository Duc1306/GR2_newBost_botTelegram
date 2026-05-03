param([int]$IntervalHours = 2)

$startup  = [Environment]::GetFolderPath('Startup')
$ws       = New-Object -ComObject WScript.Shell
$lnkPath  = "$startup\newsbot-fetch-daemon.lnk"

# Xoa shortcut cu neu ton tai
if (Test-Path $lnkPath) { Remove-Item $lnkPath -Force }

$shortcut = $ws.CreateShortcut($lnkPath)
$shortcut.TargetPath       = 'c:\Users\84328\botTele\scripts\fetch_daemon.cmd'
$shortcut.Arguments        = "$IntervalHours"
$shortcut.WorkingDirectory = 'c:\Users\84328\botTele'
$shortcut.WindowStyle      = 7   # Minimized window
$shortcut.Description      = "NewsBot - Auto fetch Telegram every $IntervalHours hour(s)"
$shortcut.Save()

Write-Host "[OK] Startup shortcut da tao: $lnkPath" -ForegroundColor Green
Write-Host "     Fetch Telegram tu dong moi $IntervalHours gio khi dang nhap Windows."
Write-Host ""
Write-Host "Go cai: chay scripts\remove_scheduler.cmd"
