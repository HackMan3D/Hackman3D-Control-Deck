$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDirectory
$Version = "1.4.11"

python -m pip install -e ".[dev]"
python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "HackMan3D Control Deck" `
    --icon "src/hackman_control_deck/assets/hcd_app_icon.ico" `
    --version-file "scripts/windows_version_info.txt" `
    --paths "src" `
    --add-data "src/hackman_control_deck/assets;hackman_control_deck/assets" `
    --collect-submodules pynput `
    run.py

$InnoSetup = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
if (-not (Test-Path $InnoSetup)) {
    $InnoSetup = Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}

if (Test-Path $InnoSetup) {
    & $InnoSetup "/DMyAppVersion=$Version" "windows_installer.iss"
    Write-Host "Installer complete: dist\HackMan3D-Control-Deck-Windows-$Version-Setup.exe"
} else {
    Write-Warning "Inno Setup 6 was not found. The portable application was built, but the installer was skipped."
}

Write-Host "Portable application: dist\HackMan3D Control Deck\HackMan3D Control Deck.exe"
