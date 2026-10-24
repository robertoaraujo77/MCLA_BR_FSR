param()
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$framework=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$output=Join-Path $root 'dist'
New-Item -ItemType Directory -Force $output | Out-Null
$name='Midnight Club L.A. Recompiled.exe'
$options=@('/nologo','/target:winexe','/platform:x64','/optimize+',
 '/reference:System.dll','/reference:System.Core.dll','/reference:System.Drawing.dll','/reference:System.Windows.Forms.dll',
 '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll','/reference:System.Web.Extensions.dll',
 "/reference:$framework\System.Xaml.dll","/reference:$framework\WPF\WindowsBase.dll","/reference:$framework\WPF\PresentationCore.dll","/reference:$framework\WPF\PresentationFramework.dll",
 "/resource:$PSScriptRoot\Launcher.xaml,MclaSetup.Launcher.xaml",
 "/resource:$PSScriptRoot\offline_bootstrap.ps1,MclaSetup.bootstrap.ps1",
 "/resource:$PSScriptRoot\assets\banner.png,MclaSetup.banner.png",
 "/resource:$PSScriptRoot\assets\logo-recompiled.png,MclaSetup.logo.png",
 "/resource:$PSScriptRoot\assets\setup.ico,MclaSetup.setup.ico",
 "/resource:$PSScriptRoot\assets\setup.ico,MclaSetup.icon.ico",
 "/win32icon:$PSScriptRoot\assets\setup.ico",
 "/out:$output\$name","$PSScriptRoot\Core.cs","$PSScriptRoot\Launcher.cs")
$options += "/resource:$root\bundle.zip,MclaSetup.offline.bundle.zip"
& (Join-Path $framework 'csc.exe') @options
if($LASTEXITCODE -ne 0){throw 'Falha ao compilar a nova interface.'}
Write-Output "Arquivo: $output\$name"
