param([Parameter(Mandatory=$true)][string]$Iso,
      [string]$ClangDirectory = "", [int]$Jobs = 4)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$sdk = Join-Path $root 'third_party/rexglue-sdk'
$install = Join-Path $sdk 'out/install/win-amd64'
function Run([string]$Command,[string[]]$Arguments) { & $Command @Arguments; if ($LASTEXITCODE -ne 0) { throw "Falha: $Command $Arguments" } }
# Execute no terminal x64 Native Tools do Visual Studio, com CMake/Ninja/Python disponíveis.
& "$PSScriptRoot/prepare_sdk.ps1"; if (-not $?) { throw 'Falha ao preparar SDK' }
Run 'python' @("$PSScriptRoot/prepare_amd_fsr.py",'--sdk',$sdk)
$compiler = @()
if ($ClangDirectory) { $compiler = @("-DCMAKE_C_COMPILER=$ClangDirectory/clang.exe","-DCMAKE_CXX_COMPILER=$ClangDirectory/clang++.exe") }
Push-Location $sdk
try {
    Run 'cmake' (@('--preset','win-amd64','-DREXGLUE_USE_VULKAN=ON','-DREXGLUE_ENABLE_TRACY=OFF','-DREXGLUE_ENABLE_FSR=ON') + $compiler)
    Run 'cmake' @('--build','out/build/win-amd64','--config','Release','--parallel',"$Jobs")
    Run 'cmake' @('--install','out/build/win-amd64','--config','Release')
} finally { Pop-Location }
Run 'python' @("$PSScriptRoot/extract_game.py",$Iso,"$root/game")
Run 'python' @("$root/localization/build_ptbr.py")
# O header de menus já acompanha os fontes; não o regenere a partir de outra revisão.
Push-Location $root
try {
    Run "$install/bin/rexglue.exe" @('codegen','mcla_manifest.toml')
    Run 'cmake' (@('--preset','win-amd64-release',"-DCMAKE_PREFIX_PATH=$install") + $compiler)
    Run 'cmake' @('--build','--preset','win-amd64-release','--parallel',"$Jobs")
    $runtime = "$root/out/build/win-amd64-release"
    Get-ChildItem "$install/bin" -Filter '*.dll' | Copy-Item -Destination $runtime -Force
    Get-ChildItem "$root/out/deps/amd-fsr" -File | Copy-Item -Destination $runtime -Force
    Run 'python' @("$PSScriptRoot/configure_install.py",'--build',$runtime)
} finally { Pop-Location }
Write-Host "Build pronto: $runtime/mcla.exe"
