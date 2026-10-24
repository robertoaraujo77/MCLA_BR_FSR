param([string]$SdkDirectory = "")
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
if (-not $SdkDirectory) { $SdkDirectory = Join-Path $root 'third_party/rexglue-sdk' }
$lock = Get-Content (Join-Path $root 'patches/dependencies.json') -Raw | ConvertFrom-Json
# The complete source archive already contains the patched dependency sources.
if (Test-Path (Join-Path $SdkDirectory '.release-source-manifest.json')) {
    & python "$PSScriptRoot/verify_sdk_snapshot.py" $SdkDirectory
    if ($LASTEXITCODE -ne 0) { throw 'A verificação dos fontes do SDK falhou.' }
    return
}
function RunGit([string[]]$Arguments) { & git @Arguments; if ($LASTEXITCODE -ne 0) { throw "Git falhou: $Arguments" } }
if (-not (Test-Path (Join-Path $SdkDirectory '.git'))) {
    RunGit @('-c','core.longpaths=true','clone','--no-checkout','https://github.com/rexglue/rexglue-sdk.git',$SdkDirectory)
    RunGit @('-C',$SdkDirectory,'checkout','--detach',$lock.sdk_commit)
    RunGit @('-C',$SdkDirectory,'-c','core.longpaths=true','submodule','update','--init','--recursive')
}
$head = (& git -C $SdkDirectory rev-parse HEAD).Trim()
if ($head -ne $lock.sdk_commit) { throw "SDK incorreto. Use um checkout limpo de $($lock.sdk_commit)." }
function Apply([string]$Repository,[string]$Patch) {
    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & git -C $Repository apply --reverse --check $Patch 2>$null
    $alreadyApplied = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $previousErrorPreference
    if ($alreadyApplied) { Write-Host "Patch já aplicado: $Patch"; return }
    RunGit @('-C',$Repository,'apply','--check',$Patch)
    RunGit @('-C',$Repository,'apply',$Patch)
}
Apply $SdkDirectory (Join-Path $root 'patches/rexglue-release.patch')
Apply (Join-Path $SdkDirectory 'thirdparty/FFmpeg') (Join-Path $root 'patches/FFmpeg.patch')
Write-Host 'SDK preparado. Consulte docs/COMPILACAO.md para compilar.'
