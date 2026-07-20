#
# Torify Installer para Windows — instala o Torify dentro do WSL.
#
# Uso (PowerShell):
#   irm https://raw.githubusercontent.com/emanueldssss/Torify-Linux/master/install.ps1 | iex
#
# Ou, com o arquivo baixado:
#   powershell -ExecutionPolicy Bypass -File install.ps1
#

$ErrorActionPreference = "Stop"

function Write-Banner {
    Write-Host ""
    Write-Host "  ████████╗ ██████╗ ██████╗ ██╗███████╗██╗   ██╗" -ForegroundColor Magenta
    Write-Host "  ╚══██╔══╝██╔═══██╗██╔══██╗██║██╔════╝╚██╗ ██╔╝" -ForegroundColor Magenta
    Write-Host "     ██║   ██║   ██║██████╔╝██║█████╗   ╚████╔╝ " -ForegroundColor DarkMagenta
    Write-Host "     ██║   ██║   ██║██╔══██╗██║██╔══╝    ╚██╔╝  " -ForegroundColor DarkMagenta
    Write-Host "     ██║   ╚██████╔╝██║  ██║██║██║        ██║   " -ForegroundColor Cyan
    Write-Host "     ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝        ╚═╝   " -ForegroundColor Cyan
    Write-Host "  ◆ Installer v2.0 — Windows (via WSL) ◆" -ForegroundColor DarkGray
    Write-Host ""
}

function Ok($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red }
function Info($msg) { Write-Host "  ➜ $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Step($msg) { Write-Host ""; Write-Host "  ◆ $msg" -ForegroundColor Magenta }

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Banner
Info "Sistema detectado: Windows $([System.Environment]::OSVersion.Version.ToString())"

# ── 1. Verifica se o WSL está disponível ───────────────────────────────
Step "Verificando WSL (Windows Subsystem for Linux)"

$wslInstalled = $false
try {
    $null = wsl.exe --status 2>&1
    $wslInstalled = $true
} catch {
    $wslInstalled = $false
}

if (-not $wslInstalled) {
    Warn "WSL não encontrado."
    Info "O Torify roda nativo no Linux — no Windows ele usa o WSL."

    if (Test-Admin) {
        Step "Instalando WSL + Ubuntu (pode pedir reinicialização)"
        wsl.exe --install -d Ubuntu
        Write-Host ""
        Warn "Se o Windows pedir para REINICIAR, reinicie e rode este script de novo."
        Write-Host ""
        Ok "WSL instalado."
    } else {
        Write-Host ""
        Err "Este script precisa de Administrador para instalar o WSL."
        Write-Host ""
        Info "Abra o PowerShell como Administrador e rode:"
        Write-Host "    wsl --install" -ForegroundColor Cyan
        Write-Host ""
        Info "Depois rode este instalador novamente."
        exit 1
    }
} else {
    Ok "WSL disponível."
}

# ── 2. Descobre a distro padrão ────────────────────────────────────────
Step "Verificando distribuição Linux no WSL"

$distros = (wsl.exe --list --quiet 2>$null) -replace "`0", "" | Where-Object { $_.Trim() -ne "" }
if (-not $distros -or $distros.Count -eq 0) {
    Warn "Nenhuma distro instalada. Instalando Ubuntu..."
    wsl.exe --install -d Ubuntu
    Warn "Conclua a criação do usuário no Ubuntu e rode este script de novo."
    exit 0
}

$defaultDistro = ($distros | Select-Object -First 1).Trim()
Ok "Distro WSL: $defaultDistro"

# ── 3. Roda o instalador Linux dentro do WSL ───────────────────────────
Step "Instalando Torify dentro do WSL ($defaultDistro)"

$installCmd = "curl -sSL https://raw.githubusercontent.com/emanueldssss/Torify-Linux/master/install.sh | bash"
Info "Executando: $installCmd"
Write-Host ""

wsl.exe -d $defaultDistro -- bash -c "$installCmd"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║   Torify instalado no WSL com sucesso!   ║" -ForegroundColor Green
    Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Info "Para usar, abra o WSL e rode:"
    Write-Host "    wsl -d $defaultDistro" -ForegroundColor Cyan
    Write-Host "    torify" -ForegroundColor Cyan
    Write-Host ""
    Info "Ou direto do Windows:"
    Write-Host "    wsl -d $defaultDistro torify" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Err "A instalação dentro do WSL falhou (código $LASTEXITCODE)."
    Info "Tente manualmente:"
    Write-Host "    wsl -d $defaultDistro" -ForegroundColor Cyan
    Write-Host "    curl -sSL https://raw.githubusercontent.com/emanueldssss/Torify-Linux/master/install.sh | bash" -ForegroundColor Cyan
    exit 1
}
