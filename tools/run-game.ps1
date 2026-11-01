# Запуск гри у вікні з журналом консолі (для перевірки локалізації)
param([string]$Extra = '')
$g = 'C:\FOLDER\Games\Call-of-Duty-World-at-War-AnkerGames'
Get-Process CoDWaW -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep 2
Remove-Item "$g\main\console.log" -ErrorAction SilentlyContinue
$args = "+set logfile 2 +set monkeytoy 0 +set r_fullscreen 0 +set r_mode 1280x720 $Extra"
Start-Process -FilePath "$g\CoDWaW.exe" -WorkingDirectory $g -ArgumentList $args
