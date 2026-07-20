#!/usr/bin/env bash
#
# Torify Installer — detecta o sistema e instala tudo automaticamente.
#
# Uso:
#   bash install.sh                 # instala a partir deste diretório
#   curl -sSL https://raw.githubusercontent.com/emanueldssss/Torify-Linux/master/install.sh | bash
#
set -e

VERSION="2.0"
REPO_RAW="https://raw.githubusercontent.com/emanueldssss/Torify-Linux/master"

# ── Cores ──────────────────────────────────────────────────────────────
if [ -t 1 ] && [ -z "$NO_COLOR" ] && [ "$TERM" != "dumb" ]; then
    RED=$'\033[91m'; GREEN=$'\033[92m'; YELLOW=$'\033[93m'
    CYAN=$'\033[96m'; MAGENTA=$'\033[95m'; GRAY=$'\033[90m'
    BOLD=$'\033[1m'; RESET=$'\033[0m'
    C_PURPLE=$'\033[38;5;135m'; C_PINK=$'\033[38;5;207m'; C_CYAN=$'\033[38;5;51m'
    TTY=1
else
    RED=""; GREEN=""; YELLOW=""; CYAN=""; MAGENTA=""; GRAY=""
    BOLD=""; RESET=""; C_PURPLE=""; C_PINK=""; C_CYAN=""; TTY=0
fi

ok()   { printf "  ${GREEN}✓${RESET} %s\n" "$1"; }
err()  { printf "  ${RED}✗${RESET} %s\n" "$1" >&2; }
info() { printf "  ${CYAN}➜${RESET} %s\n" "$1"; }
warn() { printf "  ${YELLOW}⚠${RESET} %s\n" "$1"; }
step() { printf "\n  ${C_PURPLE}◆${RESET} ${BOLD}%s${RESET}\n" "$1"; }

# ── Spinner em bash ────────────────────────────────────────────────────
SPIN_PID=""
spin_start() {
    [ "$TTY" = "0" ] && { printf "  [*] %s\n" "$1"; return; }
    (   frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
        i=0
        while true; do
            printf "\r  ${CYAN}%s${RESET} %s   " "${frames[$((i % 10))]}" "$1"
            i=$((i + 1))
            sleep 0.08
        done
    ) &
    SPIN_PID=$!
    disown 2>/dev/null || true
}
spin_stop() {
    [ -n "$SPIN_PID" ] && kill "$SPIN_PID" 2>/dev/null; wait "$SPIN_PID" 2>/dev/null
    SPIN_PID=""
    [ "$TTY" = "1" ] && printf "\r\033[K"
}
trap spin_stop EXIT

# ── Banner ─────────────────────────────────────────────────────────────
banner() {
    [ "$TTY" = "1" ] && clear
    printf "${C_PURPLE}%s${RESET}\n" "  ████████╗ ██████╗ ██████╗ ██╗███████╗██╗   ██╗"
    printf "${C_PURPLE}%s${RESET}\n" "  ╚══██╔══╝██╔═══██╗██╔══██╗██║██╔════╝╚██╗ ██╔╝"
    printf "${C_PINK}%s${RESET}\n"   "     ██║   ██║   ██║██████╔╝██║█████╗   ╚████╔╝ "
    printf "${C_PINK}%s${RESET}\n"   "     ██║   ██║   ██║██╔══██╗██║██╔══╝    ╚██╔╝  "
    printf "${C_CYAN}%s${RESET}\n"   "     ██║   ╚██████╔╝██║  ██║██║██║        ██║   "
    printf "${C_CYAN}%s${RESET}\n"   "     ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝        ╚═╝   "
    printf "  ${GRAY}◆ Installer v%s — detecta seu sistema e instala tudo ◆${RESET}\n" "$VERSION"
    echo
}

# ── Detecção do sistema operacional ────────────────────────────────────
detect_os() {
    case "$(uname -s)" in
        Linux*)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        Darwin*)  echo "macos" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *)        echo "unknown" ;;
    esac
}

detect_distro() {
    if command -v apt-get >/dev/null 2>&1; then echo "debian";  return; fi
    if command -v dnf     >/dev/null 2>&1; then echo "fedora";  return; fi
    if command -v pacman  >/dev/null 2>&1; then echo "arch";    return; fi
    if command -v zypper  >/dev/null 2>&1; then echo "suse";    return; fi
    if command -v apk     >/dev/null 2>&1; then echo "alpine";  return; fi
    echo "unknown"
}

# Roda comando como root (sudo se necessário)
as_root() {
    if [ "$(id -u)" = "0" ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        err "Precisa de root ou sudo para: $*"
        return 1
    fi
}

# ── Instalação de dependências ─────────────────────────────────────────
install_deps_linux() {
    local distro="$1"
    step "Instalando dependências do sistema ($distro)"

    local update_cmd install_cmd pkgs
    case "$distro" in
        debian) update_cmd="apt-get update";            install_cmd="apt-get install -y";        pkgs="python3 tor torsocks curl wget" ;;
        fedora) update_cmd="dnf check-update || true";  install_cmd="dnf install -y";            pkgs="python3 tor torsocks curl wget" ;;
        arch)   update_cmd="pacman -Sy";                install_cmd="pacman -S --noconfirm";     pkgs="python tor torsocks curl wget" ;;
        suse)   update_cmd="zypper refresh";            install_cmd="zypper install -y";         pkgs="python3 tor torsocks curl wget" ;;
        alpine) update_cmd="apk update";                install_cmd="apk add";                   pkgs="python3 tor torsocks curl wget bash" ;;
        *)
            err "Distro não reconhecida. Instale manualmente: python3 tor torsocks curl wget"
            exit 1
            ;;
    esac

    spin_start "Atualizando repositórios..."
    as_root sh -c "$update_cmd" >/dev/null 2>&1 || true
    spin_stop

    spin_start "Instalando: $pkgs"
    if as_root sh -c "$install_cmd $pkgs" >/dev/null 2>&1; then
        spin_stop
        ok "Dependências instaladas: $pkgs"
    else
        spin_stop
        err "Falha na instalação. Tente manualmente: sudo $install_cmd $pkgs"
        exit 1
    fi
}

install_deps_macos() {
    step "Instalando dependências via Homebrew (macOS)"

    if ! command -v brew >/dev/null 2>&1; then
        info "Homebrew não encontrado. Instalando..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
            err "Falha ao instalar Homebrew."
            exit 1
        }
    fi

    spin_start "brew install tor curl wget"
    brew install tor curl wget >/dev/null 2>&1 || true
    spin_stop

    # torsocks pode não existir no brew — não é fatal
    spin_start "brew install torsocks (opcional)"
    brew install torsocks >/dev/null 2>&1 || true
    spin_stop
    command -v torsocks >/dev/null 2>&1 || warn "torsocks indisponível no brew — o Torify usa --socks5 direto como fallback."

    ok "Dependências instaladas (macOS)"
}

# ── Instala o torify no sistema ────────────────────────────────────────
install_torify_bin() {
    step "Instalando o comando 'torify'"

    local lib_dir="$HOME/.local/lib/torify"
    local bin_dir="$HOME/.local/bin"
    local target="$lib_dir/torify.py"

    mkdir -p "$lib_dir" "$bin_dir"

    # Se torify.py existe no diretório atual, usa ele. Senão, baixa do GitHub.
    if [ -f "$(dirname "$0")/torify.py" ]; then
        cp "$(dirname "$0")/torify.py" "$target"
        ok "Copiado torify.py do diretório local"
    else
        spin_start "Baixando torify.py do GitHub..."
        if command -v curl >/dev/null 2>&1; then
            curl -sSL "$REPO_RAW/torify.py" -o "$target"
        else
            wget -q "$REPO_RAW/torify.py" -O "$target"
        fi
        spin_stop
        ok "Baixado torify.py do GitHub"
    fi
    chmod +x "$target"

    # Wrapper executável
    cat > "$bin_dir/torify" <<'EOF'
#!/usr/bin/env bash
exec python3 "$HOME/.local/lib/torify/torify.py" "$@"
EOF
    chmod +x "$bin_dir/torify"

    # Garante que ~/.local/bin está no PATH
    case ":$PATH:" in
        *":$bin_dir:"*) ;;
        *)
            for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
                if [ -f "$rc" ] || [ "$rc" = "$HOME/.profile" ]; then
                    if ! grep -q '.local/bin' "$rc" 2>/dev/null; then
                        printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$rc"
                    fi
                fi
            done
            warn "Adicione ~/.local/bin ao PATH (já incluído no seu .bashrc/.profile)"
            info "Nesta sessão, rode: export PATH=\"\$HOME/.local/bin:\$PATH\""
            ;;
    esac

    ok "Comando instalado em $bin_dir/torify"
}

# ── Verificação final ──────────────────────────────────────────────────
verify() {
    step "Verificando instalação"
    local all_ok=1
    for cmd in python3 tor curl wget; do
        if command -v "$cmd" >/dev/null 2>&1; then
            ok "$cmd encontrado"
        else
            err "$cmd NÃO encontrado"
            all_ok=0
        fi
    done
    if command -v torsocks >/dev/null 2>&1; then
        ok "torsocks encontrado"
    else
        warn "torsocks não encontrado (opcional — fallback via curl --socks5)"
    fi
    [ "$all_ok" = "1" ]
}

# ── Windows: orienta para WSL ──────────────────────────────────────────
windows_notice() {
    banner
    echo
    warn "Windows detectado (Git Bash/MSYS)."
    echo
    info "O Torify roda nativo no Linux. No Windows, ele funciona dentro do WSL."
    echo
    printf "  ${BOLD}Opção 1 — WSL (recomendado):${RESET}\n"
    printf "    ${GRAY}Abra o PowerShell como Administrador e rode:${RESET}\n"
    printf "    ${CYAN}wsl --install${RESET}\n"
    printf "    ${GRAY}Depois, dentro do Ubuntu WSL:${RESET}\n"
    printf "    ${CYAN}curl -sSL %s/install.sh | bash${RESET}\n" "$REPO_RAW"
    echo
    printf "  ${BOLD}Opção 2 — PowerShell:${RESET}\n"
    printf "    ${CYAN}irm https://raw.githubusercontent.com/emanueldssss/Torify-Linux/master/install.ps1 | iex${RESET}\n"
    echo
    exit 0
}

# ── Main ───────────────────────────────────────────────────────────────
main() {
    local os
    os=$(detect_os)

    case "$os" in
        windows) windows_notice ;;
        unknown)
            err "Sistema operacional não suportado: $(uname -s)"
            exit 1
            ;;
    esac

    banner

    case "$os" in
        wsl)    info "Sistema detectado: ${BOLD}Windows (WSL)${RESET}" ;;
        linux)  info "Sistema detectado: ${BOLD}Linux ($(detect_distro))${RESET}" ;;
        macos)  info "Sistema detectado: ${BOLD}macOS ($(uname -m))${RESET}" ;;
    esac
    info "Arquitetura: $(uname -m)"
    echo

    case "$os" in
        linux|wsl) install_deps_linux "$(detect_distro)" ;;
        macos)     install_deps_macos ;;
    esac

    install_torify_bin

    echo
    if verify; then
        echo
        printf "  ${GREEN}${BOLD}╔══════════════════════════════════════════╗${RESET}\n"
        printf "  ${GREEN}${BOLD}║   Torify instalado com sucesso!          ║${RESET}\n"
        printf "  ${GREEN}${BOLD}╚══════════════════════════════════════════╝${RESET}\n"
        echo
        info "Rode: ${BOLD}${CYAN}torify${RESET}"
        info "Ou:   ${BOLD}${CYAN}python3 ~/.local/lib/torify/torify.py${RESET}"
        echo
    else
        echo
        err "Instalação incompleta — verifique os erros acima."
        exit 1
    fi
}

main "$@"
