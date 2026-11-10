[CmdletBinding()]
param(
    [ValidatePattern('^COM[1-9][0-9]*$')]
    [string]$Port
)

$ErrorActionPreference = 'Stop'
try {
    $availablePorts = @([System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object -Unique)
} catch {
    [Console]::Error.WriteLine("Gagal membaca daftar port serial: " + $_.Exception.Message)
    exit 2
}

$report = [ordered]@{ port_tersedia = $availablePorts }
$exitCode = 0
if ($PSBoundParameters.ContainsKey('Port')) {
    $report.port_diperiksa = $Port.ToUpperInvariant()
    $report.ditemukan = $availablePorts -contains $Port
    if (-not $report.ditemukan) {
        $exitCode = 1
    }
}

$report | ConvertTo-Json
exit $exitCode
