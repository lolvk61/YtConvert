$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$bin = Join-Path $PSScriptRoot 'bin'
$scratch = Join-Path ([System.IO.Path]::GetTempPath()) ('MediaStudio-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $bin, $scratch -Force | Out-Null
try {
    if (-not ((Get-Command ffmpeg.exe -ErrorAction SilentlyContinue) -and
              (Get-Command ffprobe.exe -ErrorAction SilentlyContinue)) -and
        -not ((Test-Path "$bin\ffmpeg.exe") -and (Test-Path "$bin\ffprobe.exe"))) {
        Write-Host 'Downloading FFmpeg and FFprobe...'
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 180 -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile "$scratch\ffmpeg.zip"
        Expand-Archive -LiteralPath "$scratch\ffmpeg.zip" -DestinationPath "$scratch\ffmpeg"
        $ffmpegFolder = Get-ChildItem -LiteralPath "$scratch\ffmpeg" -Directory | Select-Object -First 1
        Copy-Item -LiteralPath "$($ffmpegFolder.FullName)\bin\ffmpeg.exe", "$($ffmpegFolder.FullName)\bin\ffprobe.exe" -Destination $bin -Force
    }
    $node = Get-Command node.exe -ErrorAction SilentlyContinue
    $nodeReady = $node -and ((& $node.Source -p 'process.versions.node.split(".")[0]') -as [int]) -ge 22
    if (-not $nodeReady -and -not (Get-Command deno.exe -ErrorAction SilentlyContinue) -and
        -not (Test-Path "$bin\deno.exe")) {
        Write-Host 'Downloading Deno...'
        $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'aarch64' } else { 'x86_64' }
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 180 -Uri "https://github.com/denoland/deno/releases/latest/download/deno-${arch}-pc-windows-msvc.zip" -OutFile "$scratch\deno.zip"
        Expand-Archive -LiteralPath "$scratch\deno.zip" -DestinationPath "$scratch\deno"
        Copy-Item -LiteralPath "$scratch\deno\deno.exe" -Destination $bin -Force
    }
}
finally {
    $resolved = (Resolve-Path -LiteralPath $scratch).Path
    if ([System.IO.Path]::GetDirectoryName($resolved) -eq [System.IO.Path]::GetTempPath().TrimEnd('\') -and
        [System.IO.Path]::GetFileName($resolved) -match '^MediaStudio-[a-f0-9-]{36}$') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
