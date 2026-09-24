# Windows : installe rustup s'il manque, puis joue les tests.
# La version du compilateur n'est pas choisie ici : rust-toolchain.toml l'impose, et rustup la télécharge au besoin.
$ErrorActionPreference = "Stop"

$cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
if (-not (Get-Command rustup -ErrorAction SilentlyContinue) -and (Test-Path $cargoBin)) {
    $env:Path = "$cargoBin;$env:Path"
}

if (-not (Get-Command rustup -ErrorAction SilentlyContinue)) {
    Write-Host "rustup absent : installation depuis https://win.rustup.rs"
    $arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "aarch64" } else { "x86_64" }
    $installer = Join-Path $env:TEMP "rustup-init.exe"
    Invoke-WebRequest -Uri "https://win.rustup.rs/$arch" -OutFile $installer
    & $installer -y --profile minimal
    $env:Path = "$cargoBin;$env:Path"
}

Set-Location $PSScriptRoot
rustup show active-toolchain
cargo test
