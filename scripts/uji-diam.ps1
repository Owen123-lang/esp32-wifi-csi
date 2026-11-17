param(
    [string]$Port = 'COM8',
    [switch]$Flash,
    [switch]$BuildOnly
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$project = Join-Path $repo 'data/build-diam-s3/project'
$build = Join-Path $project 'build'

if ($BuildOnly) {
    if ($Flash) { throw 'Pilih -BuildOnly atau -Flash.' }
    $baseline = Join-Path $repo 'data/build-s3-local/project'
    $main = Join-Path $project 'main'
    New-Item -ItemType Directory -Force $main | Out-Null
    foreach ($name in 'CMakeLists.txt','sdkconfig','sdkconfig.defaults','dependencies.lock') {
        Copy-Item -LiteralPath (Join-Path $baseline $name) -Destination $project
    }
    foreach ($name in 'CMakeLists.txt','idf_component.yml') {
        Copy-Item -LiteralPath (Join-Path "$baseline/main" $name) -Destination $main
    }
    Copy-Item -LiteralPath "$repo/firmware/diagnostik-s3/app_main.c" -Destination $main
    . 'C:/Espressif/tools/Microsoft.v5.4.2.PowerShell_profile.ps1'
    Push-Location $project
    try {
        idf.py build
        if ($LASTEXITCODE -ne 0) { throw 'Build diagnostik gagal.' }
    } finally { Pop-Location }
    return
}

if ($Flash) {
    if (!(Test-Path "$build/project.bin" -PathType Leaf)) {
        throw 'Build diagnostik belum tersedia. Jalankan skrip dengan -BuildOnly.'
    }
    Push-Location $build
    try {
        & 'C:/Espressif/tools/python/v5.4.2/venv/Scripts/python.exe' -m esptool --chip esp32s3 --port $Port --baud 460800 --before default_reset --after hard_reset write_flash '@flash_args'
        if ($LASTEXITCODE -ne 0) { throw 'Flash gagal. Periksa port dan tutup monitor serial lain.' }
    } finally { Pop-Location }
}

& "$repo/.venv/Scripts/python.exe" "$PSScriptRoot/uji_diam_gain.py" --port $Port
exit $LASTEXITCODE
