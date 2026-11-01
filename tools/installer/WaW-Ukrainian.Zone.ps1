# Зони гри Call of Duty: World at War (fastfile) для інсталятора WaW-Ukrainian.ps1:
# розпакування, запаковування й Adler-32.

# Fastfile: 12 байтів заголовка ("IWffu100" + версія), далі потік zlib: 2 байти, deflate, Adler-32 (big-endian)
function Expand-Zone([byte[]]$file) {
    $inflate = [IO.Compression.DeflateStream]::new([IO.MemoryStream]::new($file, 14, $file.Length - 14),
        [IO.Compression.CompressionMode]::Decompress)
    $out = [IO.MemoryStream]::new()
    $inflate.CopyTo($out)
    $inflate.Close()
    return , $out.ToArray()
}

function Compress-Zone([byte[]]$file, [byte[]]$data, [uint32]$adler) {
    $out = [IO.MemoryStream]::new()
    $out.Write($file, 0, 12)
    $out.WriteByte(0x78)
    $out.WriteByte(0xDA)
    $deflate = [IO.Compression.DeflateStream]::new($out, [IO.Compression.CompressionLevel]::Optimal, $true)
    $deflate.Write($data, 0, $data.Length)
    $deflate.Close()
    foreach ($shift in 24, 16, 8, 0) { $out.WriteByte([byte](($adler -shr $shift) -band 0xFF)) }
    return , $out.ToArray()
}

# Adler-32 нових даних – від старого значення з кінця файлу, лише по змінених байтах:
# A = 1 + сума байтів, B = сума (n - i) * байт[i] + n, обидва за модулем 65521
function Update-Adler([byte[]]$file, [long]$length, $changes) {
    $n = $file.Length
    $old = ([long]$file[$n - 4] -shl 24) -bor ([long]$file[$n - 3] -shl 16) -bor ([long]$file[$n - 2] -shl 8) -bor [long]$file[$n - 1]
    $a = $old -band 0xFFFF
    $b = ($old -shr 16) -band 0xFFFF
    foreach ($c in $changes) {
        for ($j = 0; $j -lt $c.From.Length; $j++) {
            $delta = [long]$c.To[$j] - [long]$c.From[$j]
            if ($delta -ne 0) {
                $a += $delta
                $b += ($length - ($c.Offset + $j)) * $delta
            }
        }
    }
    $a = (($a % 65521) + 65521) % 65521
    $b = (($b % 65521) + 65521) % 65521
    return [uint32](($b -shl 16) -bor $a)
}
