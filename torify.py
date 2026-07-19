#!/usr/bin/env python3
"""
Torify v1.1 — Linux
Roteie qualquer aplicativo Linux pelo Tor com um clique.
Auto-instala tudo na primeira execução.

Usa torsocks (nativo Tor) em vez de proxychains.

Uso:
    python3 torify.py              # Modo interativo
    python3 torify.py --install    # Apenas instala dependências
    python3 torify.py --tor        # Inicia Tor e mostra IP
"""

import os, sys, subprocess, shutil, time, json, textwrap, glob, signal, platform
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR  = Path.home() / ".config" / "torify"
TOR_DIR   = BASE_DIR / "tor"
APPS_FILE = BASE_DIR / "apps.txt"
TORRC     = BASE_DIR / "torrc"
TORSOCKS_CONF = BASE_DIR / "torsocks.conf"
MARKER    = BASE_DIR / ".setup-complete"
VENV_DIR  = BASE_DIR / "venv"

# Ports — usamos portas alternativas para não conflitar com Tor do sistema
SOCKS_PORT = 9052
CTRL_PORT  = 9053

# ── Colours ────────────────────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAGENTA= "\033[95m"
GRAY   = "\033[90m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

tor_proc: subprocess.Popen | None = None
tor_started_by_us: bool = False  # Track if WE started Tor (vs system)


# ── Platform check ─────────────────────────────────────────────────────
def check_platform():
    """Ensure we're running on Linux/WSL."""
    if platform.system() == "Windows":
        c("Este script deve ser executado no Linux ou WSL!", color=RED)
        c("No Windows, use o WSL:", color=YELLOW)
        c("  wsl.exe -d Ubuntu-24.04 python3 torify.py", color=GRAY)
        sys.exit(1)
    if platform.system() != "Linux":
        c(f"Sistema não suportado: {platform.system()}", color=RED)
        c("Use Linux ou WSL.", color=YELLOW)
        sys.exit(1)


# ── Helpers ────────────────────────────────────────────────────────────
def c(*args, color="", bold=False, sep=" "):
    text = sep.join(str(a) for a in args)
    if bold:   text = f"{BOLD}{text}{RESET}"
    if color:  text = f"{color}{text}{RESET}"
    print(text)

def err(msg): c(f"[!] {msg}", color=RED)
def ok(msg):  c(f"[+] {msg}", color=GREEN)
def info(msg): c(f"[*] {msg}", color=CYAN)


# ── Full system dependencies ───────────────────────────────────────────
ALL_DEPS = {
    "debian": {
        "pkgs": ["python3", "tor", "torsocks", "curl", "wget", "zenity", "xterm"],
        "update": ["apt-get", "update"],
    },
    "fedora": {
        "pkgs": ["python3", "tor", "torsocks", "curl", "wget", "zenity", "xterm"],
        "update": ["dnf", "check-update"],
    },
    "arch": {
        "pkgs": ["python3", "tor", "torsocks", "curl", "wget", "zenity", "xterm"],
        "update": ["pacman", "-Sy"],
    },
    "suse": {
        "pkgs": ["python3", "tor", "torsocks", "curl", "wget", "zenity", "xterm"],
        "update": ["zypper", "refresh"],
    },
    "alpine": {
        "pkgs": ["python3", "tor", "torsocks", "curl", "wget", "zenity", "xterm"],
        "update": ["apk", "update"],
    },
}

def install_all_deps(cmdline: bool = False) -> bool:
    """Install ALL system dependencies from scratch."""
    distro = detect_distro()
    deps = ALL_DEPS.get(distro)
    if not deps:
        err(f"Distro '{distro}' não suportada para instalação automática.")
        c("  Instale manualmente: python3 tor torsocks curl wget", color=YELLOW)
        return False

    pkgs = deps["pkgs"]
    missing = [p for p in pkgs if not shutil.which(p) and not p.startswith("python")]

    # Always ensure python3 is installed (check via python3 --version)
    try:
        subprocess.run(["python3", "--version"], capture_output=True)
    except:
        missing.insert(0, "python3")

    if cmdline:
        c(f"\n  [*] Instalando dependências para {distro}...", color=CYAN)
        c(f"  [*] Pacotes: {', '.join(pkgs)}\n", color=GRAY)

    if not missing:
        if cmdline:
            ok("Todas as dependências já estão instaladas!")
        return True

    if cmdline:
        c(f"  [*] Instalando: {', '.join(missing)}\n", color=YELLOW)

    # Update package lists first
    update_cmd = deps["update"]
    run_as_root(update_cmd)

    # Install
    success = install_pkgs(missing)
    if success:
        if cmdline:
            ok("Todas as dependências instaladas!")
        return True
    else:
        err(f"Falha ao instalar: {', '.join(missing)}")
        if cmdline:
            c("  Tente manualmente:", color=YELLOW)
            c(f"  sudo apt install {' '.join(missing)}", color=GRAY)
        return False


# ── Auto-install ───────────────────────────────────────────────────────
def detect_distro() -> str:
    if shutil.which("apt-get"):  return "debian"
    if shutil.which("dnf"):      return "fedora"
    if shutil.which("pacman"):   return "arch"
    if shutil.which("zypper"):   return "suse"
    if shutil.which("apk"):      return "alpine"
    return "unknown"

def run_as_root(cmd: list[str]) -> bool:
    """Run a command as root (sudo if available, else direct)."""
    if os.geteuid() == 0:
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except:
            return False
    sudo = shutil.which("sudo")
    if sudo:
        try:
            subprocess.run([sudo, *cmd], check=True, capture_output=True)
            return True
        except:
            return False
    return False

def install_pkgs(pkgs: list[str]) -> bool:
    distro = detect_distro()
    cmds = {
        "debian": ["apt-get", "install", "-y"],
        "fedora": ["dnf", "install", "-y"],
        "arch":   ["pacman", "-S", "--noconfirm"],
        "suse":   ["zypper", "install", "-y"],
        "alpine": ["apk", "add"],
    }
    base = cmds.get(distro)
    if not base:
        err(f"Distro '{distro}' não suportada. Instale manualmente: {', '.join(pkgs)}")
        return False
    return run_as_root([*base, *pkgs])

def ensure_tor() -> str | None:
    """Ensure tor binary is available, auto-install if needed."""
    tor_bin = shutil.which("tor")
    if tor_bin:
        return tor_bin

    info("Tor não encontrado. Instalando...")
    if install_pkgs(["tor"]):
        tor_bin = shutil.which("tor")
        if tor_bin:
            ok("Tor instalado!")
            return tor_bin

    # fallback: download expert bundle
    err("Instalação via pacote falhou. Baixando Expert Bundle...")
    try:
        import urllib.request, tarfile
        arch_map = {"x86_64": "x86_64", "i686": "i686", "aarch64": "aarch64"}
        arch = arch_map.get(platform.machine(), "x86_64")
        url = f"https://www.torproject.org/dist/torbrowser/15.0.18/tor-expert-bundle-linux-{arch}-15.0.18.tar.gz"
        dest = BASE_DIR / "tor-dl.tar.gz"
        urllib.request.urlretrieve(url, dest)
        with tarfile.open(dest) as tf:
            tf.extractall(path=TOR_DIR)
        dest.unlink()
        tor_bin = next(TOR_DIR.rglob("tor"), None)
        if tor_bin:
            tor_bin.chmod(0o755)
            ok(f"Tor baixado: {tor_bin}")
            return str(tor_bin)
    except Exception as e:
        err(f"Falha no download: {e}")
    return None

def ensure_torsocks() -> str | None:
    """Ensure torsocks is available, auto-install if needed."""
    ts = shutil.which("torsocks")
    if ts:
        return ts

    info("torsocks não encontrado. Instalando...")
    if install_pkgs(["torsocks"]):
        ts = shutil.which("torsocks")
        if ts:
            ok(f"torsocks instalado: {ts}")
            return ts
    err("torsocks não disponível.")
    return None

def write_configs():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    TORRC.write_text(textwrap.dedent(f"""\
        SocksPort {SOCKS_PORT}
        ControlPort {CTRL_PORT}
        CookieAuthentication 0
        Log notice file /dev/null
    """).lstrip())
    # torsocks.conf — aponta pro Tor do Torify (porta alternativa)
    TORSOCKS_CONF.write_text(textwrap.dedent(f"""\
        # torsocks.conf — gerado pelo Torify
        TorAddress 127.0.0.1
        TorPort {SOCKS_PORT}
        OnionAddrRange 127.42.42.0/24
        AllowOutboundLocalhost 1
    """).lstrip())
    ok("Configurações criadas em ~/.config/torify/")

def auto_setup():
    """Auto-install everything on first run."""
    c("\n  ========================", color=MAGENTA, bold=True)
    c("    Primeira Execução", color=MAGENTA, bold=True)
    c("  ========================\n", color=MAGENTA, bold=True)

    info("Verificando dependências do sistema...\n")
    install_all_deps(cmdline=False)

    info("Verificando Tor...\n")
    tor_path = ensure_tor()

    info("Verificando torsocks...\n")
    ts_path = ensure_torsocks()

    write_configs()
    MARKER.write_text("setup complete")

    if tor_path:
        ok("Tor pronto!")
    if ts_path:
        ok("torsocks pronto!")
    c("")


# ── Tor management ─────────────────────────────────────────────────────
def check_port(host: str, port: int, timeout: float = 2) -> bool:
    """Check if a TCP port is open."""
    import socket as _s
    try:
        s = _s.socket(_s.AF_INET, _s.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def kill_our_tor():
    """Kill our managed Tor process if running."""
    global tor_proc
    if tor_proc and tor_proc.poll() is None:
        tor_proc.terminate()
        try:
            tor_proc.wait(timeout=5)
        except:
            tor_proc.kill()
        tor_proc = None
        time.sleep(1)

def start_tor():
    global tor_proc, tor_started_by_us
    if tor_proc and tor_proc.poll() is None:
        return True

    # Check if OUR Tor is already running on the alternative ports
    our_socks = check_port("127.0.0.1", SOCKS_PORT)
    our_ctrl  = check_port("127.0.0.1", CTRL_PORT)

    if our_socks and our_ctrl and tor_proc and tor_proc.poll() is None:
        ok(f"Tor do Torify já está rodando (SOCKS5 :{SOCKS_PORT}, Control :{CTRL_PORT})")
        return True

    # Ports in use but we don't own the process — kill and retake control
    if our_socks or our_ctrl:
        info("Porta ocupada. Retomando controle do Tor...")
        for cmd in [
            ["fuser", "-k", f"{SOCKS_PORT}/tcp"],
            ["fuser", "-k", f"{CTRL_PORT}/tcp"],
        ]:
            try:
                subprocess.run(cmd, capture_output=True, timeout=5)
            except:
                pass
        time.sleep(1)

    tor_bin = ensure_tor()
    if not tor_bin:
        err("Tor não disponível. Impossível continuar.")
        return False

    if not TORRC.exists():
        write_configs()

    info("Iniciando Tor (portas alternativas)...")
    try:
        tor_proc = subprocess.Popen(
            [tor_bin, "-f", str(TORRC)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(4)
        if tor_proc.poll() is not None:
            err("Tor falhou ao iniciar.")
            return False
        tor_started_by_us = True
        ok(f"Tor rodando (SOCKS5 :{SOCKS_PORT}, Control :{CTRL_PORT})")
        return True
    except Exception as e:
        err(f"Erro ao iniciar Tor: {e}")
        return False

def send_newnym():
    try:
        import socket
        s = socket.create_connection(("127.0.0.1", CTRL_PORT), timeout=5)
        s.sendall(b"AUTHENTICATE\r\n")
        s.recv(1024)
        s.sendall(b"SIGNAL NEWNYM\r\n")
        s.recv(1024)
        s.close()
        return True
    except Exception as e:
        err(f"Falha ao rotacionar IP: {e}")
        return False

def get_ip(use_tor: bool = False, url="https://api.ipify.org") -> str:
    """Get public IP. If use_tor=True, routes through Tor SOCKS5."""
    if use_tor:
        # curl via SOCKS5 proxy (porta alternativa do Torify)
        for cmd in [
            ["curl", "-s", "--max-time", "10", "--socks5", f"127.0.0.1:{SOCKS_PORT}", url],
            ["curl", "-s", "--max-time", "10", "--proxy", f"socks5://127.0.0.1:{SOCKS_PORT}", url],
        ]:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
            except: continue
        # fallback: torsocks wrapper
        for base in [["curl", "-s", "--max-time", "10"],
                     ["wget", "-qO-", "--timeout=10"]]:
            try:
                r = subprocess.run(["torsocks", *base, url], capture_output=True, text=True, timeout=15)
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
            except: continue
        return "?"

    # direct (no Tor)
    for cmd in [["curl", "-s", "--max-time", "5"],
                ["wget", "-qO-", "--timeout=5"]]:
        try:
            r = subprocess.run([*cmd, url], capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except: continue
    return "?"


# ── torsocks wrapper ───────────────────────────────────────────────────
def get_torsocks_bin() -> str | None:
    """Find the torsocks wrapper binary."""
    return shutil.which("torsocks")


# ── App management ─────────────────────────────────────────────────────
def load_apps() -> list[dict]:
    if not APPS_FILE.exists():
        return []
    apps = []
    for line in APPS_FILE.read_text().strip().splitlines():
        if not line.strip(): continue
        parts = line.split("|", 1)
        if len(parts) == 2:
            apps.append({"name": parts[0].strip(), "path": parts[1].strip()})
    return apps

def save_apps(apps: list[dict]):
    APPS_FILE.parent.mkdir(parents=True, exist_ok=True)
    APPS_FILE.write_text("\n".join(f"{a['name']}|{a['path']}" for a in apps) + "\n")

def find_target_app() -> str | None:
    candidates = [
        "discord", "telegram-desktop", "signal-desktop", "firefox",
        "chromium", "google-chrome", "chromium-browser", "slack",
        "thunderbird", "hexchat", "irssi", "weechat", "transmission-gtk",
    ]
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None

def add_app_interactive():
    apps = load_apps()
    c("\n  Como adicionar o app?", color=CYAN)
    c("  1) Selecionar com janela (zenity/kdialog)")
    c("  2) Digitar o caminho manualmente")
    c("  0) Voltar\n")
    choice = input("  > ").strip()

    path = None
    if choice == "1":
        for dialog in ["zenity --file-selection --title='Selecione o executável'",
                        "kdialog --getopenfilename --title 'Selecione o executável'"]:
            try:
                r = subprocess.run(dialog.split(), capture_output=True, text=True, timeout=15)
                if r.returncode == 0 and r.stdout.strip():
                    path = r.stdout.strip()
                    break
            except: continue
        if not path:
            err("Nenhum diálogo disponível. Instale zenity ou kdialog.")
            return
    elif choice == "2":
        c("  Digite o caminho completo do executável:", color=GRAY)
        path = input("  > ").strip()
        if not os.path.isfile(path):
            err("Arquivo não encontrado.")
            return
    else:
        return

    name = os.path.basename(path)
    apps.append({"name": name, "path": path})
    save_apps(apps)
    ok(f"'{name}' adicionado!")


# ── UI ─────────────────────────────────────────────────────────────────
def logo():
    os.system("clear || cls")
    c("")
    c("  ========================", color=MAGENTA, bold=True)
    c("    Torify v1.1 — Linux", color=MAGENTA, bold=True)
    c("  ========================", color=MAGENTA, bold=True)
    c("  Tor + torsocks for Linux", color=GRAY)
    c("  ========================", color=MAGENTA, bold=True)
    c("  Roteie qualquer app Linux", color=GRAY)
    c("  pelo Tor com um clique.", color=GRAY)
    c("  ========================\n", color=MAGENTA, bold=True)

def draw_menu():
    logo()
    c("  [1] Rodar Torify", color=CYAN)
    c("      Inicia Tor e rotaciona IP\n")
    c("  [2] Conferir IP", color=CYAN)
    c("      Mostra IP real vs IP do Tor\n")
    c("  [3] Configurar", color=CYAN)
    c("      Define o app padrão\n")
    c("  [4] Adicionar App", color=CYAN)
    c("      Seleciona um binário/AppImage\n")
    c("  [5] Abrir App com Tor", color=CYAN)
    c("      Lista apps salvos e abre com torsocks\n")
    c("  [00] Parar Tor", color=RED)
    c("       Mata o Tor e restaura IP normal\n")
    c("  [0] Sair\n")
    return input("  > ").strip()


# ── Options ────────────────────────────────────────────────────────────
def option_torify():
    logo()
    info("Iniciando Torify...\n")
    if not start_tor():
        input("  Pressione Enter para continuar...")
        return
    info("Rotacionando IP...")
    send_newnym()
    time.sleep(2)
    ok("IP rotacionado!\n")

    real = get_ip(use_tor=False)
    info(f"IP real (sem Tor): {real}")
    tor_ip = get_ip(use_tor=True)
    c(f"IP pelo Tor:        {tor_ip}", color=GREEN)

    if real and tor_ip and real != tor_ip:
        c("\n  [+] Proxy funcionando! IPs diferentes.", color=GREEN)
    elif real and tor_ip:
        c("\n  [!] IPs iguais — verifique se o Tor está rodando.", color=YELLOW)
    c("")

def option_check_ip():
    logo()
    info("Verificando IPs...\n")
    real = get_ip(use_tor=False)
    info(f"IP real (sem Tor): {real}")
    tor_ip = get_ip(use_tor=True)
    c(f"IP pelo Tor:        {tor_ip}", color=GREEN)

    if real and tor_ip and real != tor_ip:
        ok("Tor está funcionando!")
    elif real and tor_ip:
        err("Tor NÃO está roteando o tráfego.")
    else:
        err("Não foi possível verificar os IPs.")
    c("")

def option_config():
    logo()
    apps = load_apps()
    auto = find_target_app()
    c("  Configuração do app padrão\n", color=CYAN)
    if auto:
        c(f"  Detectado automaticamente: {auto}", color=GRAY)
    elif apps:
        c(f"  Último app configurado: {apps[-1]['path']}", color=GRAY)
    else:
        c("  Nenhum caminho configurado.", color=GRAY)
    c("  Digite o caminho completo do executável")
    c("  (Enter para manter, 'auto' para detectar, 'reset' para limpar):\n", color=GRAY)
    path = input("  > ").strip()

    if path == "":
        return
    elif path.lower() == "auto":
        found = find_target_app()
        if found:
            save_apps([{"name": os.path.basename(found), "path": found}])
            ok(f"Configurado: {found}")
        else:
            err("Nada detectado.")
    elif path.lower() == "reset":
        save_apps([])
        APPS_FILE.unlink(missing_ok=True)
        ok("Configuração resetada.")
    else:
        if os.path.isfile(path):
            save_apps([{"name": os.path.basename(path), "path": path}])
            ok(f"Configurado: {path}")
        else:
            err("Arquivo não encontrado.")
    c("")

def option_launch_app():
    apps = load_apps()
    if not apps:
        err("Nenhum app configurado. Use a opção 4 primeiro.")
        return

    logo()
    c("  Apps salvos:\n", color=CYAN)
    for i, app in enumerate(apps, 1):
        c(f"  [{i}] {app['name']}", color=GREEN)
        c(f"      {app['path']}", color=GRAY)

    c("\n  [0] Voltar\n", color=GRAY)
    choice = input("  > ").strip()
    if choice == "0" or choice == "":
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(apps):
            err("Opção inválida.")
            return
    except ValueError:
        err("Número inválido.")
        return

    app = apps[idx]
    if not os.path.isfile(app["path"]):
        err(f"Arquivo não encontrado: {app['path']}")
        return

    if not start_tor():
        return

    ts = get_torsocks_bin()
    if not ts:
        err("torsocks não encontrado.")
        return

    c(f"\n  [*] Abrindo '{app['name']}' com Tor...", color=CYAN)
    c(f"      TORSOCKS_CONF_FILE={TORSOCKS_CONF} {ts} {app['path']}\n", color=GRAY)

    try:
        env = os.environ.copy()
        env["TORSOCKS_CONF_FILE"] = str(TORSOCKS_CONF)
        subprocess.Popen(
            [ts, app["path"]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        ok(f"'{app['name']}' iniciado com Tor!")
    except Exception as e:
        err(f"Erro ao iniciar: {e}")
    c("")

def option_stop_tor():
    """Kill our Tor process and restore normal IP."""
    global tor_started_by_us
    logo()
    if not tor_proc or tor_proc.poll() is not None:
        info("Tor do Torify não está rodando.\n")
        return

    info("Parando Tor do Torify...")
    kill_our_tor()
    tor_started_by_us = False
    ok("Tor parado. Tráfego não passa mais pelo Torify.")
    c("  IP real restaurado.\n", color=GRAY)

def option_add_app():
    logo()
    add_app_interactive()


# ── CLI ────────────────────────────────────────────────────────────────
def cli_install():
    """Install all dependencies and exit."""
    c("\n  ========================", color=MAGENTA, bold=True)
    c("    Instalação completa", color=MAGENTA, bold=True)
    c("  ========================\n", color=MAGENTA, bold=True)
    ok = install_all_deps(cmdline=True)
    sys.exit(0 if ok else 1)

def cli_tor():
    """Start Tor, show IP, and exit."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    if not MARKER.exists():
        auto_setup()
    if start_tor():
        send_newnym()
        time.sleep(2)
        real = get_ip(use_tor=False)
        tor_ip = get_ip(use_tor=True)
        info(f"IP real: {real}")
        info(f"IP Tor:  {tor_ip}")
        sys.exit(0)
    sys.exit(1)


# ── Main ───────────────────────────────────────────────────────────────
def main():
    check_platform()

    # CLI argumentos
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("--install", "-i"):
            cli_install()
        elif arg in ("--tor", "-t"):
            cli_tor()
        elif arg in ("--help", "-h"):
            c("""Uso: python3 torify.py [OPÇÃO]

Opções:
  --install, -i    Instala todas as dependências do sistema
  --tor, -t        Inicia Tor e mostra IP real vs IP pelo Tor
  --help, -h       Mostra esta ajuda

Sem argumentos: modo interativo
""")
            sys.exit(0)
        else:
            err(f"Argumento desconhecido: {arg}")
            c("Use --help para ajuda.", color=YELLOW)
            sys.exit(1)

    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Auto-setup na primeira execução
    if not MARKER.exists():
        auto_setup()
        if not MARKER.exists():
            err("Setup incompleto.")
            sys.exit(1)

    while True:
        op = draw_menu()

        if op == "1":
            option_torify()
        elif op == "2":
            option_check_ip()
        elif op == "3":
            option_config()
        elif op == "4":
            option_add_app()
        elif op == "5":
            option_launch_app()
        elif op == "00":
            option_stop_tor()
        elif op == "0":
            c("\n  Até mais!\n", color=MAGENTA)
            kill_our_tor()
            sys.exit(0)
        else:
            err("Opção inválida.\n")

        input("  Pressione Enter para continuar...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        c("\n  Até mais!\n", color=MAGENTA)
        kill_our_tor()
        sys.exit(0)
    except Exception as e:
        err(f"Erro: {e}")
        sys.exit(1)
