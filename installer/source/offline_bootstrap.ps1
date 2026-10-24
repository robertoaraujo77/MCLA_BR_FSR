param(
    [Parameter(Mandatory=$true)][string]$Iso,
    [Parameter(Mandatory=$true)][string]$InstallDirectory,
    [Parameter(Mandatory=$true)][string]$InstallerDirectory,
    [Parameter(Mandatory=$true)][string]$GraphicsSettings,
    [Parameter(Mandatory=$true)][string]$BundleDirectory
)
$ErrorActionPreference = 'Stop'
try {
    $python = Join-Path $BundleDirectory 'tools\python\python.exe'
    $prepare = Join-Path $BundleDirectory 'compact_prepare.py'
    if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $prepare)) {
        throw 'Extraia todo o ZIP em uma pasta antes de abrir o assistente.'
    }
    $env:PYTHONUNBUFFERED = '1'
    $env:PYTHONUTF8 = '1'
    & $python -u $prepare --bundle $BundleDirectory --destination $InstallDirectory --iso $Iso --installer-dir $InstallerDirectory --graphics-settings $GraphicsSettings
    if ($LASTEXITCODE -ne 0) { throw 'A preparacao nao terminou. Consulte o registro acima.' }
    exit 0
} catch {
    Write-Output ('ERRO: ' + $_.Exception.Message)
    exit 1
}
