<#
  Find-LowBitrate.ps1 — list songs under 192 kbps so you know what to re-get
  as FLAC. Windows only, nothing to install (uses Windows' own file
  properties, the same numbers File Explorer shows in "Bit rate").

  Double-click "Find Low Bitrate Songs.bat", or drag a music folder onto it.
  Writes LowBitrate-Report.html + .csv to your Desktop and opens the report.
  Read-only: nothing is moved, changed or deleted.
#>
param([string]$Path, [string]$OutDir, [int]$Threshold = 192)

$ErrorActionPreference = 'Stop'
$audio    = '.mp3','.m4a','.aac','.mp4','.ogg','.opus','.wma','.flac','.wav','.ape','.aiff','.aif','.dsf','.dff','.wv'
$lossless = '.flac','.wav','.ape','.aiff','.aif','.dsf','.dff','.wv'
$plays    = '.flac','.mp3','.wav'      # what ReChord can decode today

if (-not $Path) {
    Add-Type -AssemblyName System.Windows.Forms
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = 'Pick your music folder (or the Echo Mini / SD card)'
    if ($dlg.ShowDialog() -ne 'OK') { exit }
    $Path = $dlg.SelectedPath
}
if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "Not a folder: $Path" }
if (-not $OutDir) { $OutDir = [Environment]::GetFolderPath('Desktop') }

function Get-Track([System.IO.FileInfo]$f, $shell) {
    $ext = $f.Extension.ToLower()
    $r = [ordered]@{ Path = $f.FullName; Ext = $ext.TrimStart('.').ToUpper(); Kbps = $null
                     Artist = ''; Album = ''; Title = ''; Lossless = ($lossless -contains $ext)
                     Plays = ($plays -contains $ext) }
    try {
        $item = $shell.Namespace($f.DirectoryName).ParseName($f.Name)
        $bps  = $item.ExtendedProperty('System.Audio.EncodingBitrate')
        if (-not $bps) {
            $dur = $item.ExtendedProperty('System.Media.Duration')       # 100 ns units
            if ($dur) { $bps = $f.Length * 8 / ($dur / 1e7) }
        }
        if ($bps) { $r.Kbps = [int][math]::Round($bps / 1000) }
        $a = $item.ExtendedProperty('System.Music.Artist'); if ($a) { $r.Artist = ($a -join ', ') }
        $r.Album = [string]$item.ExtendedProperty('System.Music.AlbumTitle')
        $r.Title = [string]$item.ExtendedProperty('System.Title')
    } catch { }
    if (($ext -eq '.m4a' -or $ext -eq '.mp4') -and $r.Kbps -gt 600) { $r.Lossless = $true }   # ALAC
    if (-not $r.Title) { $r.Title = [IO.Path]::GetFileNameWithoutExtension($f.Name) }
    [pscustomobject]$r
}

Write-Host "Scanning $Path ..." -ForegroundColor Cyan
$shell = New-Object -ComObject Shell.Application
$files = Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue |
         Where-Object { $audio -contains $_.Extension.ToLower() -and -not $_.Name.StartsWith('._') }
$i = 0
$rows = foreach ($f in $files) {
    $i++; if ($i % 50 -eq 0) { Write-Progress -Activity 'Reading bitrates' -Status "$i / $($files.Count)" -PercentComplete (100 * $i / [math]::Max(1,$files.Count)) }
    Get-Track $f $shell
}
Write-Progress -Activity 'Reading bitrates' -Completed
$rows    = @($rows)
$low     = @($rows | Where-Object { -not $_.Lossless -and $_.Kbps -and $_.Kbps -lt $Threshold } |
             Sort-Object Artist, Album, Kbps)
$unknown = @($rows | Where-Object { -not $_.Kbps -and -not $_.Lossless })
$noplay  = @($rows | Where-Object { -not $_.Plays })

$csv = Join-Path $OutDir 'LowBitrate-Report.csv'
$low | Select-Object Kbps, Ext, Artist, Album, Title, Path | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8

$sep = [string][char]1   # group key separator (works on Windows PowerShell 5.1)
function E([string]$s) { [System.Net.WebUtility]::HtmlEncode($s) }
$groups = $low | Group-Object { "$(if($_.Artist){$_.Artist}else{'Unknown artist'})$sep$(if($_.Album){$_.Album}else{'Unknown album'})" } |
          Sort-Object { ($_.Group | Measure-Object Kbps -Minimum).Minimum }

$sb = New-Object System.Text.StringBuilder
[void]$sb.Append(@'
<!doctype html><meta charset="utf-8"><title>Low bitrate report</title>
<style>
body{background:#110d1f;color:#eef4ff;font:15px/1.45 Consolas,Menlo,monospace;margin:0;padding:24px}
h1{color:#ff3fbf;font-size:26px;margin:0 0 4px}.sub{color:#8a86b0;margin-bottom:20px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 22px}
.stat{background:#1d1833;border-left:3px solid #3ff0e0;padding:10px 14px}
.stat b{display:block;font-size:22px;color:#3ff0e0}
details{background:#1d1833;margin:0 0 8px;border-left:3px solid #ff3b4f}
summary{cursor:pointer;padding:10px 14px}summary .k{color:#b6ff5a;float:right}
table{width:100%;border-collapse:collapse}td{padding:4px 14px;border-top:1px solid #2a2448}
td.k{color:#ff3b4f;width:70px}.p{color:#8a86b0;font-size:12px;word-break:break-all}
h2{color:#3ff0e0;font-size:17px;margin:26px 0 8px}
</style>
'@)
[void]$sb.Append("<h1>LOW BITRATE // REPORT</h1><div class=sub>$(Get-Date -Format 'yyyy-MM-dd HH:mm') &middot; scanned $(E $Path) &middot; under $Threshold kbps</div>")
[void]$sb.Append("<div class=stats><div class=stat><b>$($rows.Count)</b>songs scanned</div><div class=stat><b>$($low.Count)</b>under $Threshold kbps</div><div class=stat><b>$(@($groups).Count)</b>albums to upgrade</div><div class=stat><b>$($noplay.Count)</b>won't play on ReChord</div></div>")
if ($low.Count -eq 0) { [void]$sb.Append("<p>Nothing under $Threshold kbps. Clean library.</p>") }
foreach ($g in $groups) {
    $artist, $album = $g.Name -split [regex]::Escape($sep), 2
    $worst = ($g.Group | Measure-Object Kbps -Minimum).Minimum
    $s = if ($g.Count -eq 1) { '' } else { 's' }
    [void]$sb.Append("<details open><summary><b>$(E $artist)</b> &mdash; $(E $album) <span class=k>$($g.Count) song$s, worst $worst kbps</span></summary><table>")
    foreach ($r in $g.Group) {
        [void]$sb.Append("<tr><td class=k>$($r.Kbps)</td><td>$(E $r.Title)<div class=p>$(E $r.Path)</div></td><td>$($r.Ext)</td></tr>")
    }
    [void]$sb.Append('</table></details>')
}
if ($noplay.Count) {
    [void]$sb.Append("<h2>Formats ReChord can't play yet ($($noplay.Count))</h2><p class=sub>ReChord plays FLAC, MP3 and WAV. Convert these or keep stock firmware for them.</p><table>")
    foreach ($r in ($noplay | Sort-Object Path | Select-Object -First 500)) {
        [void]$sb.Append("<tr><td class=k>$($r.Ext)</td><td>$(E $r.Title)<div class=p>$(E $r.Path)</div></td></tr>")
    }
    [void]$sb.Append('</table>')
}
if ($unknown.Count) {
    [void]$sb.Append("<h2>Couldn't read bitrate ($($unknown.Count))</h2><table>")
    foreach ($r in ($unknown | Select-Object -First 200)) { [void]$sb.Append("<tr><td class=p>$(E $r.Path)</td></tr>") }
    [void]$sb.Append('</table>')
}
$html = Join-Path $OutDir 'LowBitrate-Report.html'
[IO.File]::WriteAllText($html, $sb.ToString(), (New-Object System.Text.UTF8Encoding $false))

Write-Host ""
Write-Host "$($low.Count) of $($rows.Count) songs are under $Threshold kbps" -ForegroundColor Magenta
Write-Host "Report: $html"
Write-Host "CSV:    $csv"
Start-Process $html
