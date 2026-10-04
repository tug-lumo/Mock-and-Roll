<#
.SYNOPSIS
  Turn 360° (equirectangular) videos and images into lightweight proxies for Mock & Roll's
  LED volume, and list them in environments\library.json so they appear in the app.

.DESCRIPTION
  For every file in -InputDir (default environments\source):
    1. Crops the sphere to the part the stage can actually see — by default 270° around
       (±135° from straight ahead) and from 40° below the horizon to 80° above — so the pixels
       go where the LED surfaces are.
    2. Scales to -Width (default 3840 px wide; most laptops/GPUs handle 4096 max texture).
    3. Videos → H.264 MP4 (yuv420p, +faststart, no audio). Images → high-quality JPEG.
    4. Adds/updates an entry in environments\library.json with the crop range, so the app maps
       the proxy back onto the right part of the sphere. Your edits to "name" and "yaw" in the
       manifest are kept on re-runs.
  Files already converted (proxy newer than source) are skipped unless -Force.

  "Straight ahead" in the source = the centre of the equirectangular frame. If the shot's
  interesting direction is elsewhere, either set -CenterLon (degrees, + = right) to recentre the
  crop, or leave it and use the app's Turn slider (stored as the manifest's "yaw").

.EXAMPLE
  .\tools\make-360-proxies.ps1
.EXAMPLE
  .\tools\make-360-proxies.ps1 -Full -Width 4096          # keep the whole sphere
.EXAMPLE
  .\tools\make-360-proxies.ps1 -CenterLon 90 -MaxSeconds 30 -Force
.EXAMPLE
  .\tools\make-360-proxies.ps1 -Width 2560                # lighter, for phones / older laptops
#>
[CmdletBinding()]
param(
  [string]$InputDir = "environments\source",
  [string]$OutputDir = "environments",
  [double]$LonMin = -135,
  [double]$LonMax = 135,
  [double]$LatMin = -40,
  [double]$LatMax = 80,
  [double]$CenterLon = 0,
  [int]$Width = 3840,
  [int]$Crf = 20,
  [string]$Preset = "slow",
  [int]$MaxSeconds = 0,
  [switch]$Full,
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not [IO.Path]::IsPathRooted($InputDir)) { $InputDir = Join-Path $root $InputDir }
if (-not [IO.Path]::IsPathRooted($OutputDir)) { $OutputDir = Join-Path $root $OutputDir }

foreach ($tool in "ffmpeg", "ffprobe") {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
    throw "$tool not found. Install FFmpeg (e.g. 'winget install Gyan.FFmpeg') and open a new terminal."
  }
}
if (-not (Test-Path $InputDir)) {
  New-Item -ItemType Directory -Force $InputDir | Out-Null
  Write-Host "Created $InputDir - put your 360 videos/images there and run this again."
  return
}
New-Item -ItemType Directory -Force $OutputDir | Out-Null

if ($Full) { $LonMin = -180; $LonMax = 180; $LatMin = -90; $LatMax = 90; $CenterLon = 0 }
if ($LonMax -le $LonMin -or $LatMax -le $LatMin) { throw "Crop range is empty: check -LonMin/-LonMax/-LatMin/-LatMax." }
if (($LonMax - $LonMin) -gt 360 -or $LatMin -lt -90 -or $LatMax -gt 90) { throw "Crop range is outside the sphere (lon span <= 360, lat -90..90)." }

$videoExt = @(".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi")
$imageExt = @(".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp")
$inv = [Globalization.CultureInfo]::InvariantCulture
function F([double]$v) { return $v.ToString("0.######", $inv) }

function Get-Slug([string]$s) {
  $t = ($s.ToLowerInvariant() -replace "[^a-z0-9]+", "-").Trim("-")
  if (-not $t) { $t = "env" }
  return $t
}
function Get-Title([string]$s) {
  $t = ($s -replace "[_\-]+", " ").Trim()
  return (Get-Culture).TextInfo.ToTitleCase($t)
}
function Get-Probe([string]$file) {
  $j = & ffprobe -v error -select_streams v:0 -show_entries stream=width,height:format=duration -of json -- "$file" | Out-String | ConvertFrom-Json
  $s = $j.streams | Select-Object -First 1
  $d = 0.0
  if ($j.format -and $j.format.duration) { [double]::TryParse([string]$j.format.duration, [Globalization.NumberStyles]::Float, $inv, [ref]$d) | Out-Null }
  return [pscustomobject]@{ W = [int]$s.width; H = [int]$s.height; Seconds = $d }
}

# Existing manifest (kept: name + yaw edits)
$manifestPath = Join-Path $OutputDir "library.json"
$manifest = @()
if (Test-Path $manifestPath) {
  $raw = Get-Content -Raw -Encoding UTF8 $manifestPath
  # Windows PowerShell returns a JSON array as one object; piping enumerates it. Keep real entries only.
  if ($raw.Trim()) { $manifest = @((ConvertFrom-Json $raw) | ForEach-Object { $_ } | Where-Object { $_ -and $_.id }) }
}

$files = Get-ChildItem -File $InputDir | Where-Object { ($videoExt + $imageExt) -contains $_.Extension.ToLowerInvariant() }
if (-not $files) { Write-Host "No 360 videos/images in $InputDir."; return }

# Crop window as fractions of the source frame (equirect: x = lon -180..180, y = lat 90..-90).
$lo = $LonMin + $CenterLon; $hi = $LonMax + $CenterLon
$cw = ($hi - $lo) / 360.0; $ch = ($LatMax - $LatMin) / 180.0
$cx = ($lo + 180.0) / 360.0; $cy = (90.0 - $LatMax) / 180.0
$wraps = ($cx -lt 0) -or ($cx + $cw -gt 1.0001)

$made = 0; $skipped = 0
foreach ($f in $files) {
  $isVideo = $videoExt -contains $f.Extension.ToLowerInvariant()
  $id = Get-Slug $f.BaseName
  $outName = $id + $(if ($isVideo) { ".mp4" } else { ".jpg" })
  $out = Join-Path $OutputDir $outName

  $p = Get-Probe $f.FullName
  if (-not $p.W -or -not $p.H) { Write-Warning "Skipping $($f.Name): no video/image stream found."; continue }
  $aspect = $p.W / [double]$p.H
  if ([math]::Abs($aspect - 2.0) -gt 0.05) {
    Write-Warning "$($f.Name) is $($p.W)x$($p.H) ($('{0:0.00}' -f $aspect):1). A full 360 equirectangular frame is 2:1 - the mapping may be off."
  }

  $fresh = (Test-Path $out) -and ((Get-Item $out).LastWriteTime -gt $f.LastWriteTime)
  if ($fresh -and -not $Force) { Write-Host "= $($f.Name) (up to date)"; $skipped++ }
  else {
    # Filter: (optional recentre by rolling the frame) -> crop -> scale.
    $vf = @()
    if ($wraps -or $CenterLon -ne 0) {
      # Roll the equirect horizontally so the crop window doesn't cross the frame edge.
      # scroll shifts the picture right by hpos*W, so hpos = -CenterLon/360 brings that direction to the centre.
      $vf += "scroll=horizontal=0:hpos=" + (F ((((-$CenterLon / 360.0) % 1) + 1) % 1))
      $cx = ($LonMin + 180.0) / 360.0
    }
    if (-not $Full) {
      $vf += "crop=w=iw*" + (F $cw) + ":h=ih*" + (F $ch) + ":x=iw*" + (F $cx) + ":y=ih*" + (F $cy)
    }
    $vf += "scale=" + $Width + ":-2:flags=lanczos"
    if ($isVideo) { $vf += "format=yuv420p" }
    $filter = $vf -join ","

    Write-Host "> $($f.Name)  ->  $outName"
    $ffArgs = @("-y", "-hide_banner", "-loglevel", "error", "-stats", "-i", $f.FullName)
    if ($isVideo -and $MaxSeconds -gt 0) { $ffArgs += @("-t", "$MaxSeconds") }
    $ffArgs += @("-vf", $filter)
    if ($isVideo) {
      $ffArgs += @("-c:v", "libx264", "-preset", $Preset, "-crf", "$Crf", "-profile:v", "high", "-movflags", "+faststart", "-an", $out)
    } else {
      $ffArgs += @("-frames:v", "1", "-q:v", "2", $out)
    }
    & ffmpeg @ffArgs
    if ($LASTEXITCODE -ne 0) { Write-Warning "ffmpeg failed on $($f.Name)."; continue }
    $made++
  }

  $q = Get-Probe $out
  $old = $manifest | Where-Object { $_.id -eq $id } | Select-Object -First 1
  $entry = [ordered]@{
    id      = $id
    name    = $(if ($old -and $old.name) { $old.name } else { Get-Title $f.BaseName })
    file    = $outName
    type    = $(if ($isVideo) { "video" } else { "image" })
    lon     = @([double]$LonMin, [double]$LonMax)
    lat     = @([double]$LatMin, [double]$LatMax)
    yaw     = $(if ($old -and $old.yaw -ne $null) { [double]$old.yaw } else { 0 })
    width   = $q.W
    height  = $q.H
    seconds = $(if ($isVideo) { [math]::Round($q.Seconds, 2) } else { 0 })
    source  = $f.Name
    made    = (Get-Date).ToString("yyyy-MM-dd")
  }
  $manifest = @($manifest | Where-Object { $_.id -ne $id }) + @([pscustomobject]$entry)
}

$manifest = @($manifest | Sort-Object name)
$json = ConvertTo-Json -InputObject $manifest -Depth 5
[IO.File]::WriteAllText($manifestPath, $json, (New-Object Text.UTF8Encoding($false)))
Write-Host ""
Write-Host "Done: $made converted, $skipped up to date. Library: $manifestPath ($($manifest.Count) environments)."
Write-Host "In Mock & Roll: LED -> 360 environment -> Library."
