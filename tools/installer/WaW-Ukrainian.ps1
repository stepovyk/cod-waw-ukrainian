# Інсталятор української локалізації Call of Duty: World at War.
# Латає файли гри гравця на місці (латки містять старі й нові байти), додає власні файли локалізації,
# а видалення повертає старі байти. Файлів Activision інсталятор не містить.
# Звичайний відкритий скрипт PowerShell без компільованих програм: увесь код видно.
#
# Запуск: WaW-Ukrainian-Setup.cmd (вікно) або тихо:
#   powershell -ExecutionPolicy Bypass -File WaW-Ukrainian.ps1 /install "тека гри"   (або /remove); код виходу 0 – успіх
param([string]$Mode, [string]$Game)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$Title = 'Call of Duty: World at War українською'
$DataFile = Join-Path $PSScriptRoot 'WaW-Ukrainian.dat'
$BackupDir = 'ukrainian_backup'
$Links = @(
    @('Підтримати переклад', 'https://send.monobank.ua/jar/8aeC9dGFrn'),
    @('Telegram', 'https://t.me/stepovyk_ua'),
    @('GitHub', 'https://github.com/stepovyk/cod-waw-ukrainian')
)
$script:Progress = { param($text) }

# ---------- дані локалізації ----------
# Типи записів: 0 – латка exe, 1 – латка зони, 2 – новий файл, 3 – заміна з резервною копією, 4 – ресурс інсталятора
function Read-Payload {
    if (-not (Test-Path -LiteralPath $DataFile)) {
        throw "Не знайдено файл WaW-Ukrainian.dat.`nРозпакуйте архів повністю й запустіть інсталятор з розпакованої теки."
    }
    $r = [IO.BinaryReader]::new([IO.File]::OpenRead($DataFile))
    try {
        if ([Text.Encoding]::ASCII.GetString($r.ReadBytes(6)) -ne 'WAWUA1') {
            throw 'Пошкоджений файл WaW-Ukrainian.dat. Завантажте архів ще раз.'
        }
        $list = [Collections.Generic.List[object]]::new()
        $count = $r.ReadInt32()
        for ($i = 0; $i -lt $count; $i++) {
            $rec = [pscustomobject]@{ Kind = [int]$r.ReadByte(); Path = ''; Patches = @(); Data = $null }
            $rec.Path = [Text.Encoding]::UTF8.GetString($r.ReadBytes($r.ReadUInt16())).Replace('/', '\')
            if ($rec.Kind -le 1) {
                $n = $r.ReadInt32()
                $rec.Patches = @(for ($k = 0; $k -lt $n; $k++) {
                    $offset = $r.ReadInt32()
                    $length = $r.ReadInt32()
                    [pscustomobject]@{ Offset = $offset; Old = $r.ReadBytes($length); New = $r.ReadBytes($length) }
                })
            }
            else { $rec.Data = $r.ReadBytes($r.ReadInt32()) }
            $list.Add($rec)
        }
        return , $list
    }
    finally { $r.Close() }
}

function Get-Resource($records, [string]$name) {
    foreach ($rec in $records) { if ($rec.Kind -eq 4 -and $rec.Path -eq $name) { return , $rec.Data } }
    return $null
}

# зони гри (fastfile) – в окремому файлі поруч
$ZoneScript = Join-Path $PSScriptRoot 'WaW-Ukrainian.Zone.ps1'
if (-not (Test-Path -LiteralPath $ZoneScript)) {
    [void][Windows.Forms.MessageBox]::Show("Не знайдено файл WaW-Ukrainian.Zone.ps1.`nРозпакуйте архів повністю й запустіть інсталятор з розпакованої теки.",
        $Title, [Windows.Forms.MessageBoxButtons]::OK, [Windows.Forms.MessageBoxIcon]::Warning)
    exit 1
}
. $ZoneScript

# ---------- встановлення ----------
function Test-GameDir([string]$dir) {
    try {
        return [bool]($dir -and (Test-Path -LiteralPath (Join-Path $dir 'CoDWaW.exe') -PathType Leaf) -and
            (Test-Path -LiteralPath (Join-Path $dir 'zone\english') -PathType Container))
    }
    catch { return $false }
}

function Test-Installed($records, [string]$game) {
    foreach ($rec in $records) {
        if ($rec.Kind -eq 2 -and (Test-Path -LiteralPath (Join-Path $game $rec.Path))) { return $true }
    }
    return $false
}

function Test-Bytes([byte[]]$buffer, [int]$offset, [byte[]]$what) {
    if ($offset + $what.Length -gt $buffer.Length) { return $false }
    for ($i = 0; $i -lt $what.Length; $i++) { if ($buffer[$offset + $i] -ne $what[$i]) { return $false } }
    return $true
}

function Read-GameData($rec, [byte[]]$file) {
    if ($rec.Kind -eq 1) { return , (Expand-Zone $file) }
    return , $file
}

function Write-GameFile([string]$path, [byte[]]$bytes) {
    $tmp = "$path.ukr-tmp"
    [IO.File]::WriteAllBytes($tmp, $bytes)
    [IO.File]::Copy($tmp, $path, $true)
    [IO.File]::Delete($tmp)
}

# $toUkrainian: $true – ставимо нові байти, $false – повертаємо старі.
# Спершу перевірка всіх файлів, потім запис: гра не лишиться напівзалатаною.
function Invoke-Patches($records, [string]$game, [bool]$toUkrainian) {
    $plan = [Collections.Generic.List[object]]::new()
    foreach ($rec in $records) {
        if ($rec.Kind -gt 1) { continue }
        & $script:Progress "Перевірка: $($rec.Path)"
        $path = Join-Path $game $rec.Path
        if (-not (Test-Path -LiteralPath $path)) { throw "Не знайдено файл гри: $($rec.Path)" }
        $data = Read-GameData $rec ([IO.File]::ReadAllBytes($path))
        $from = 0
        $to = 0
        foreach ($p in $rec.Patches) {
            if ($toUkrainian) { $src = $p.Old; $dst = $p.New } else { $src = $p.New; $dst = $p.Old }
            if (Test-Bytes $data $p.Offset $src) { $from++ }
            elseif (Test-Bytes $data $p.Offset $dst) { $to++ }
            else {
                throw "Ця версія файлу не підтримується: $($rec.Path)`nПотрібна Call of Duty: World at War версії 1.7 з англійською мовою."
            }
        }
        if ($from -gt 0 -and $to -gt 0) { throw "Файл змінено частково: $($rec.Path)" }
        if ($from -gt 0) { $plan.Add($rec) }
    }
    foreach ($rec in $plan) {
        & $script:Progress ($(if ($toUkrainian) { 'Встановлення: ' } else { 'Відновлення: ' }) + $rec.Path)
        $path = Join-Path $game $rec.Path
        $file = [IO.File]::ReadAllBytes($path)
        $data = Read-GameData $rec $file
        $changes = foreach ($p in $rec.Patches) {
            if ($toUkrainian) { [pscustomobject]@{ Offset = $p.Offset; From = $p.Old; To = $p.New } }
            else { [pscustomobject]@{ Offset = $p.Offset; From = $p.New; To = $p.Old } }
        }
        foreach ($c in $changes) { [Array]::Copy($c.To, 0, $data, $c.Offset, $c.To.Length) }
        if ($rec.Kind -eq 1) { Write-GameFile $path (Compress-Zone $file $data (Update-Adler $file $data.Length $changes)) }
        else { Write-GameFile $path $data }
    }
}

# Стандартні назви своїх класів зберігаються в профілі гравця (seta customclassN "Custom N")
function Set-ClassNames([bool]$toUkrainian) {
    $root = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Activision\CoDWaW\players\profiles'
    if (-not (Test-Path -LiteralPath $root)) { return }
    $enc = [Text.Encoding]::GetEncoding(1251)
    foreach ($cfg in Get-ChildItem -LiteralPath $root -Recurse -Filter 'config*.cfg' -File) {
        try {
            $text = $enc.GetString([IO.File]::ReadAllBytes($cfg.FullName))
            $result = $text
            for ($n = 1; $n -le 10; $n++) {
                $en = "seta customclass$n `"Custom $n`""
                $uk = "seta customclass$n `"Свій клас $n`""
                if ($toUkrainian) { $result = $result.Replace($en, $uk) } else { $result = $result.Replace($uk, $en) }
            }
            if ($result -ne $text) { [IO.File]::WriteAllBytes($cfg.FullName, $enc.GetBytes($result)) }
        }
        catch [IO.IOException] { }
    }
}

function Install-Localization($records, [string]$game) {
    Invoke-Patches $records $game $true
    foreach ($rec in $records) {
        if ($rec.Kind -ne 2 -and $rec.Kind -ne 3) { continue }
        $path = Join-Path $game $rec.Path
        if ($rec.Kind -eq 3) {
            $backup = Join-Path (Join-Path $game $BackupDir) $rec.Path
            if (-not (Test-Path -LiteralPath $backup) -and (Test-Path -LiteralPath $path)) {
                [void][IO.Directory]::CreateDirectory((Split-Path -Parent $backup))
                [IO.File]::Copy($path, $backup)
            }
        }
        & $script:Progress "Встановлення: $($rec.Path)"
        [void][IO.Directory]::CreateDirectory((Split-Path -Parent $path))
        [IO.File]::WriteAllBytes($path, $rec.Data)
    }
    Set-ClassNames $true
}

function Remove-Localization($records, [string]$game) {
    Invoke-Patches $records $game $false
    foreach ($rec in $records) {
        $path = Join-Path $game $rec.Path
        if ($rec.Kind -eq 2 -and (Test-Path -LiteralPath $path)) { [IO.File]::Delete($path) }
        if ($rec.Kind -eq 3) {
            $backup = Join-Path (Join-Path $game $BackupDir) $rec.Path
            if (Test-Path -LiteralPath $backup) {
                [IO.File]::Copy($backup, $path, $true)
                [IO.File]::Delete($backup)
            }
        }
    }
    $dir = Join-Path $game $BackupDir
    if ((Test-Path -LiteralPath $dir) -and -not (Get-ChildItem -LiteralPath $dir -Recurse -File)) {
        Remove-Item -LiteralPath $dir -Recurse
    }
    Set-ClassNames $false
}

# Будь-які інсталятори гри (диск, Steam, інші збірки) записують теку в реєстр
function Find-Game {
    $candidates = [Collections.Generic.List[string]]::new()
    $candidates.Add($PSScriptRoot)
    $candidates.Add((Split-Path -Parent $PSScriptRoot))
    $keys = @(
        @('HKLM:\SOFTWARE\WOW6432Node\Activision\Call of Duty WAW', 'InstallPath'),
        @('HKLM:\SOFTWARE\Activision\Call of Duty WAW', 'InstallPath'),
        @('HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 10090', 'InstallLocation'),
        @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 10090', 'InstallLocation')
    )
    foreach ($k in $keys) {
        $value = (Get-ItemProperty -LiteralPath $k[0] -ErrorAction SilentlyContinue).($k[1])
        if ($value) { $candidates.Add($value) }
    }
    foreach ($root in 'HKLM:', 'HKCU:') {
        foreach ($branch in 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', 'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall') {
            foreach ($app in Get-ChildItem -LiteralPath "$root\$branch" -ErrorAction SilentlyContinue) {
                $p = Get-ItemProperty -LiteralPath $app.PSPath -ErrorAction SilentlyContinue
                if ($p.DisplayName -like '*World at War*' -and $p.InstallLocation) { $candidates.Add($p.InstallLocation) }
            }
        }
    }
    foreach ($c in $candidates) { if (Test-GameDir $c) { return $c.TrimEnd('\') } }
    return ''
}

function Test-CanWrite([string]$game) {
    try {
        $probe = Join-Path $game 'zone\english\.ukr-probe'
        [IO.File]::WriteAllText($probe, '')
        [IO.File]::Delete($probe)
        return $true
    }
    catch { return $false }
}

function Test-GameRunning {
    return [bool](Get-Process -Name 'CoDWaW', 'CoDWaWmp' -ErrorAction SilentlyContinue)
}

# Помилки .NET приходять загорнутими: беремо першопричину й пояснюємо її людською мовою
function Get-ErrorText($record) {
    $e = $record.Exception
    while ($e.InnerException) { $e = $e.InnerException }
    if ($e -is [UnauthorizedAccessException]) { return 'Немає доступу до теки гри. Запустіть інсталятор від імені адміністратора.' }
    return $e.Message
}

function Show-Warning([string]$text) {
    [void][Windows.Forms.MessageBox]::Show($text, $Title, [Windows.Forms.MessageBoxButtons]::OK, [Windows.Forms.MessageBoxIcon]::Warning)
}

# ---------- тихий режим ----------
if ($Mode -eq '/install' -or $Mode -eq '/remove') {
    try {
        if (-not (Test-GameDir $Game)) { throw "Не знайдено гру: $Game" }
        $records = Read-Payload
        if ($Mode -eq '/install') { Install-Localization $records $Game } else { Remove-Localization $records $Game }
        exit 0
    }
    catch {
        Show-Warning (Get-ErrorText $_)
        exit 1
    }
}

# ---------- вікно ----------
[Windows.Forms.Application]::EnableVisualStyles()
try { $records = Read-Payload }
catch {
    Show-Warning (Get-ErrorText $_)
    exit 1
}

$Ink = [Drawing.Color]::FromArgb(240, 240, 240)
$Muted = [Drawing.Color]::FromArgb(160, 164, 170)
$Back = [Drawing.Color]::FromArgb(22, 24, 27)
$Panel = [Drawing.Color]::FromArgb(36, 39, 44)
$Accent = [Drawing.Color]::FromArgb(255, 205, 0)
$Dark = [Drawing.Color]::FromArgb(20, 20, 20)
$Off = [Drawing.Color]::FromArgb(90, 94, 100)

$form = [Windows.Forms.Form]@{
    Text = $Title; FormBorderStyle = 'FixedSingle'; MaximizeBox = $false; StartPosition = 'CenterScreen'
    BackColor = $Back; ForeColor = $Ink; Font = [Drawing.Font]::new('Segoe UI', 10)
    ClientSize = [Drawing.Size]::new(600, 470)
}
$iconPng = Get-Resource $records 'icon.png'
if ($iconPng) { $form.Icon = [Drawing.Icon]::FromHandle(([Drawing.Bitmap]::new([IO.MemoryStream]::new($iconPng))).GetHicon()) }

$banner = [Windows.Forms.PictureBox]@{ BackColor = $Panel; SizeMode = 'Zoom'; Bounds = [Drawing.Rectangle]::new(0, 0, 600, 200) }
$bannerPng = Get-Resource $records 'banner.png'
if ($bannerPng) { $banner.Image = [Drawing.Bitmap]::new([IO.MemoryStream]::new($bannerPng)) }
$form.Controls.Add($banner)

$form.Controls.Add([Windows.Forms.Label]@{ Text = 'Тека з грою'; ForeColor = $Muted; AutoSize = $true; Location = [Drawing.Point]::new(24, 218) })

# поле з внутрішніми відступами: рамка – панель, сам текст без рамки
$field = [Windows.Forms.Panel]@{ BackColor = $Panel; Bounds = [Drawing.Rectangle]::new(24, 240, 440, 32) }
$path = [Windows.Forms.TextBox]@{ BorderStyle = 'None'; BackColor = $Panel; ForeColor = $Ink; Bounds = [Drawing.Rectangle]::new(10, 7, 420, 20) }
$field.Controls.Add($path)
$field.Add_Click({ $path.Focus() })
$form.Controls.Add($field)

function New-Button([string]$text, [bool]$primary, [int]$x, [int]$y, [int]$w, [int]$h) {
    $b = [Windows.Forms.Button]@{
        Text = $text; FlatStyle = 'Flat'; Cursor = 'Hand'; Bounds = [Drawing.Rectangle]::new($x, $y, $w, $h)
        Font = [Drawing.Font]::new('Segoe UI Semibold', 11)
    }
    $b.FlatAppearance.BorderSize = 0
    $b.BackColor = $(if ($primary) { $Accent } else { $Panel })
    $b.ForeColor = $(if ($primary) { $Dark } else { $Ink })
    $form.Controls.Add($b)
    return $b
}
$browse = New-Button 'Огляд…' $false 472 240 104 32
$install = New-Button 'Встановити' $true 24 292 270 46
$remove = New-Button 'Видалити' $false 306 292 270 46

$status = [Windows.Forms.Label]@{ ForeColor = $Muted; Bounds = [Drawing.Rectangle]::new(24, 350, 552, 56) }
$form.Controls.Add($status)

$x = 24
foreach ($link in $Links) {
    $l = [Windows.Forms.LinkLabel]@{
        Text = $link[0]; AutoSize = $true; LinkColor = $Accent; ActiveLinkColor = $Ink; VisitedLinkColor = $Accent
        LinkBehavior = 'HoverUnderline'; Location = [Drawing.Point]::new($x, 424); Tag = $link[1]
    }
    $l.Add_LinkClicked({ param($s) Start-Process $s.Tag })
    $form.Controls.Add($l)
    $x += [Windows.Forms.TextRenderer]::MeasureText($link[0], $form.Font).Width + 28
}

function Update-State {
    $ok = Test-GameDir $path.Text
    $installed = $ok -and (Test-Installed $records $path.Text)
    $install.Enabled = $ok
    $remove.Enabled = $installed
    $install.Text = $(if ($installed) { 'Оновити' } else { 'Встановити' })
    # пласкі кнопки не показують вимкнений стан самі
    $install.BackColor = $(if ($ok) { $Accent } else { $Panel })
    $install.ForeColor = $(if ($ok) { $Dark } else { $Muted })
    $remove.ForeColor = $(if ($installed) { $Ink } else { $Off })
    $status.Text = $(if (-not $ok) { 'Вкажіть теку гри – ту, де лежить CoDWaW.exe.' }
        elseif ($installed) { 'Українську локалізацію встановлено.' } else { 'Гру знайдено. Можна встановлювати.' })
}

function Invoke-Action([bool]$toUkrainian) {
    if (Test-GameRunning) {
        [void][Windows.Forms.MessageBox]::Show($form, 'Спершу закрийте гру.', $Title,
            [Windows.Forms.MessageBoxButtons]::OK, [Windows.Forms.MessageBoxIcon]::Information)
        return
    }
    $game = $path.Text.TrimEnd('\')
    $done = $(if ($toUkrainian) { 'Готово! Запускайте гру.' } else { 'Локалізацію видалено, гра знову англійською.' })
    if (-not (Test-CanWrite $game)) {
        # тека в Program Files потребує прав адміністратора: перезапуск з підвищенням лише тоді
        $ok = $false
        try {
            $arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}" {1} "{2}"' -f $PSCommandPath, $(if ($toUkrainian) { '/install' } else { '/remove' }), $game
            $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -Verb RunAs -Wait -PassThru
            $ok = $p.ExitCode -eq 0
        }
        catch { }
        Update-State
        if ($ok) { $status.Text = $done }
        return
    }
    foreach ($c in $install, $remove, $browse, $path) { $c.Enabled = $false }
    $form.UseWaitCursor = $true
    $script:Progress = { param($text) $status.Text = $text; [Windows.Forms.Application]::DoEvents() }
    $problem = $null
    try { if ($toUkrainian) { Install-Localization $records $game } else { Remove-Localization $records $game } }
    catch { $problem = Get-ErrorText $_ }
    $script:Progress = { param($text) }
    $form.UseWaitCursor = $false
    $browse.Enabled = $true
    $path.Enabled = $true
    Update-State
    if ($problem) {
        $status.Text = $problem
        [void][Windows.Forms.MessageBox]::Show($form, $problem, $Title, [Windows.Forms.MessageBoxButtons]::OK, [Windows.Forms.MessageBoxIcon]::Warning)
    }
    else { $status.Text = $done }
}

$browse.Add_Click({
    $d = [Windows.Forms.FolderBrowserDialog]@{ Description = 'Оберіть теку, де лежить CoDWaW.exe' }
    if ($d.ShowDialog($form) -eq 'OK') { $path.Text = $d.SelectedPath }
})
$install.Add_Click({ Invoke-Action $true })
$remove.Add_Click({ Invoke-Action $false })
$path.Add_TextChanged({ Update-State })

# консоль запускача згорнута, тож вікно інсталятора явно показуємо звичайним і на передньому плані
$form.Add_Shown({ $form.WindowState = 'Normal'; $form.Activate() })

$path.Text = Find-Game
Update-State
[void]$form.ShowDialog()
