param(
    [ValidateSet('tx','rx-a','rx-b')][string]$Role = 'rx-a',
    [string]$Port,
    [switch]$Flash
)
$ErrorActionPreference = 'Stop'
$taskFirmwareRoot = $PSScriptRoot
if (-not (Get-Command idf.py -ErrorAction SilentlyContinue)) {
    throw 'Activate the ESP-IDF v5.4.3 environment before running this script.'
}
if ($Flash -and -not $Port) { throw '-Port is required with -Flash' }
Push-Location -LiteralPath $taskFirmwareRoot
try {
    & idf.py -B "build-$Role" -D "IDF_TARGET=esp32s3" -D "SDKCONFIG=sdkconfig.$Role" -D "SDKCONFIG_DEFAULTS=sdkconfig.defaults;profiles/$Role.defaults" build
    if ($LASTEXITCODE -ne 0) { throw 'Firmware build failed' }
    $taskSdkConfig = Get-Content -Raw -LiteralPath "sdkconfig.$Role"
    if (-not $taskSdkConfig.Contains("CONFIG_CSI_DEVICE_ID=`"$Role`"")) {
        throw 'Generated SDK configuration does not match the selected board role'
    }
    $taskAppBinary = Join-Path "build-$Role" 'skripsi_csi_pilot.bin'
    $taskProjectDescription = Get-Content -Raw -LiteralPath (Join-Path "build-$Role" 'project_description.json') | ConvertFrom-Json
    $taskBuildManifest = [ordered]@{
        role = $Role
        target = 'esp32s3'
        idf_version = $taskProjectDescription.idf_ver
        git_commit = (& git rev-parse HEAD)
        application_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $taskAppBinary).Hash.ToLowerInvariant()
        sdkconfig_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath "sdkconfig.$Role").Hash.ToLowerInvariant()
        source_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath 'main/app_main.c').Hash.ToLowerInvariant()
        flashed = $false
    }
    $taskManifestPath = Join-Path "build-$Role" 'flash-manifest.json'
    $taskBuildManifest | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $taskManifestPath
    if ($Flash) {
        & idf.py -B "build-$Role" -p $Port flash
        if ($LASTEXITCODE -ne 0) { throw 'Flashing failed' }
        $taskBuildManifest.flashed = $true
        $taskBuildManifest | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $taskManifestPath
    }
} finally { Pop-Location }
