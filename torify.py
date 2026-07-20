#!/usr/bin/env python3
"""
Torify v2.0 — Linux
Roteie qualquer aplicativo Linux pelo Tor com um clique.
Auto-instala tudo na primeira execução.

Usa torsocks (nativo Tor) em vez de proxychains.

Uso:
    python3 torify.py              # Modo interativo
    python3 torify.py --install    # Apenas instala dependências
    python3 torify.py --tor        # Inicia Tor e mostra IP
"""

import os, sys, subprocess, shutil, time, json, textwrap, glob, signal, platform
import threading, re, itertools
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR  = Path.home() / ".config" / "torify"
TOR_DIR   = BASE_DIR / "tor"
APPS_FILE = BASE_DIR / "apps.txt"
TORRC     = BASE_DIR / "torrc"
TORSOCKS_CONF = BASE_DIR / "torsocks.conf"
MARKER    = BASE_DIR / ".setup-complete"
LOG_FILE  = BASE_DIR / "tor.log"
VENV_DIR  = BASE_DIR / "venv"

# Ports — usamos portas alternativas para não conflitar com Tor do sistema
SOCKS_PORT = 9052
CTRL_PORT  = 9053

VERSION = "2.0"

# ── Colours ────────────────────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAGENTA= "\033[95m"
GRAY   = "\033[90m"
WHITE  = "\033[97m"
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

# Detecta suporte a ANSI / terminal interativo
IS_TTY = sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb" \
         and not os.environ.get("NO_COLOR")

def _c256(n: int) -> str:
    return f"\033[38;5;{n}m"

# Paleta do gradiente: roxo Tor -> magenta -> cyan
PALETTE = [93, 99, 135, 171, 207, 51]

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
    if not IS_TTY:
        color = ""
        bold = False
    if bold:   text = f"{BOLD}{text}{RESET}"
    if color:  text = f"{color}{text}{RESET}"
    print(text)

def err(msg): c(f"  {RED}✗{RESET} {msg}" if IS_TTY else f"[!] {msg}")
def ok(msg):  c(f"  {GREEN}✓{RESET} {msg}" if IS_TTY else f"[+] {msg}")
def info(msg): c(f"  {CYAN}➜{RESET} {msg}" if IS_TTY else f"[*] {msg}")
def warn(msg): c(f"  {YELLOW}⚠{RESET} {msg}" if IS_TTY else f"[!] {msg}")


# ── Animation engine ───────────────────────────────────────────────────
def gradient_text(text: str, palette=PALETTE) -> str:
    """Aplica gradiente de cores 256 ao texto."""
    if not IS_TTY:
        return text
    out = []
    n = len(palette)
    for i, ch in enumerate(text):
        color = palette[int(i / max(len(text) - 1, 1) * (n - 1))]
        out.append(f"{_c256(color)}{ch}")
    return "".join(out) + RESET


def typewriter(text: str, delay: float = 0.018, color=""):
    """Efeito de máquina de escrever."""
    if not IS_TTY:
        print(text)
        return
    for ch in text:
        sys.stdout.write(f"{color}{ch}{RESET}" if color else ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


class Spinner:
    """Spinner animado em thread. Uso: with Spinner('msg'): ..."""
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, msg: str, color=CYAN):
        self.msg = msg
        self.color = color
        self._stop = threading.Event()
        self._thread = None
        self.active = IS_TTY

    def _spin(self):
        for frame in itertools.cycle(self.FRAMES):
            if self._stop.is_set():
                break
            sys.stdout.write(f"\r  {self.color}{frame}{RESET} {self.msg}   ")
            sys.stdout.flush()
            time.sleep(0.07)
        sys.stdout.write("\r" + " " * (len(self.msg) + 12) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        if self.active:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            print(f"  [*] {self.msg}")
        return self

    def done(self, msg: str = None, success: bool = True):
        """Finaliza o spinner mostrando ✓ ou ✗."""
        self._stop.set()
        if self._thread:
            self._thread.join()
        if msg:
            if success:
                ok(msg)
            else:
                err(msg)

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join()
        return False


def progress_bar(percent: int, msg: str = "", width: int = 34):
    """Desenha uma barra de progresso na linha atual."""
    if not IS_TTY:
        return
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    bar_colored = gradient_text(bar, PALETTE)
    sys.stdout.write(f"\r  {bar_colored} {BOLD}{percent:3d}%{RESET} {GRAY}{msg}{RESET}   ")
    sys.stdout.flush()


def clear_line():
    if IS_TTY:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


# ── Banner ─────────────────────────────────────────────────────────────
BANNER = [
    "████████╗ ██████╗ ██████╗ ██╗███████╗██╗   ██╗",
    "╚══██╔══╝██╔═══██╗██╔══██╗██║██╔════╝╚██╗ ██╔╝",
    "   ██║   ██║   ██║██████╔╝██║█████╗   ╚████╔╝ ",
    "   ██║   ██║   ██║██╔══██╗██║██╔══╝    ╚██╔╝  ",
    "   ██║   ╚██████╔╝██║  ██║██║██║        ██║   ",
    "   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝        ╚═╝   ",
]

def print_banner(animated: bool = True):
    """Banner com gradiente + animação linha a linha."""
    if not IS_TTY:
        for line in BANNER:
            print(line)
        print(f"  Torify v{VERSION} — Roteie qualquer app pelo Tor")
        return
    for i, line in enumerate(BANNER):
        color = _c256(PALETTE[int(i / (len(BANNER) - 1) * (len(PALETTE) - 1))])
        sys.stdout.write(f"  {color}{line}{RESET}\n")
        sys.stdout.flush()
        if animated:
            time.sleep(0.045)
    subtitle = f"◆ v{VERSION} — Roteie qualquer app pelo Tor com um clique ◆"
    typewriter(f"  {gradient_text(subtitle)}", delay=0.008)


def draw_status_bar():
    """Barra de status do Tor no topo do menu."""
    running = check_port("127.0.0.1", SOCKS_PORT, timeout=0.5)
    if running:
        dot = f"{GREEN}●{RESET}" if IS_TTY else "[ON]"
        status = f"Tor {dot} {GRAY}SOCKS5 :{SOCKS_PORT}{RESET}"
    else:
        dot = f"{RED}●{RESET}" if IS_TTY else "[OFF]"
        status = f"Tor {dot} {GRAY}parado{RESET}"
    c(f"  {status}")


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
        info(f"Distribuição detectada: {BOLD}{distro}{RESET}")
        info(f"Pacotes necessários: {', '.join(pkgs)}")

    if not missing:
        if cmdline:
            ok("Todas as dependências já estão instaladas!")
        return True

    # Update package lists first
    update_cmd = deps["update"]
    with Spinner("Atualizando lista de pacotes..."):
        run_as_root(update_cmd)

    # Install
    spin = Spinner(f"Instalando: {', '.join(missing)}")
    spin.__enter__()
    success = install_pkgs(missing)
    spin.__exit__()
    if success:
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

    spin = Spinner("Tor não encontrado. Instalando...")
    spin.__enter__()
    if install_pkgs(["tor"]):
        tor_bin = shutil.which("tor")
        if tor_bin:
            spin.__exit__()
            ok("Tor instalado!")
            return tor_bin
    spin.__exit__()

    # fallback: download expert bundle
    warn("Instalação via pacote falhou. Baixando Expert Bundle...")
    try:
        import urllib.request, tarfile
        arch_map = {"x86_64": "x86_64", "i686": "i686", "aarch64": "aarch64"}
        arch = arch_map.get(platform.machine(), "x86_64")
        url = f"https://www.torproject.org/dist/torbrowser/15.0.18/tor-expert-bundle-linux-{arch}-15.0.18.tar.gz"
        dest = BASE_DIR / "tor-dl.tar.gz"
        with Spinner("Baixando Tor Expert Bundle..."):
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

    spin = Spinner("torsocks não encontrado. Instalando...")
    spin.__enter__()
    if install_pkgs(["torsocks"]):
        ts = shutil.which("torsocks")
        if ts:
            spin.__exit__()
            ok(f"torsocks instalado: {ts}")
            return ts
    spin.__exit__()
    err("torsocks não disponível.")
    return None

def write_configs():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    TORRC.write_text(textwrap.dedent(f"""\
        SocksPort {SOCKS_PORT}
        ControlPort {CTRL_PORT}
        CookieAuthentication 0
        Log notice file {LOG_FILE}
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
    if IS_TTY:
        os.system("clear")
    print_banner(animated=True)
    c("")
    c(f"  {gradient_text('─' * 46)}")
    c(f"  {BOLD}{MAGENTA}PRIMEIRA EXECUÇÃO — SETUP AUTOMÁTICO{RESET}" if IS_TTY else "PRIMEIRA EXECUÇÃO — SETUP AUTOMÁTICO")
    c(f"  {gradient_text('─' * 46)}")
    c("")

    install_all_deps(cmdline=False)

    tor_path = ensure_tor()
    ts_path = ensure_torsocks()

    write_configs()
    MARKER.write_text("setup complete")

    c("")
    if tor_path:
        ok("Tor pronto!")
    if ts_path:
        ok("torsocks pronto!")
    c("")
    time.sleep(0.6)


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
    """Kill any Tor process on our ports — managed or not."""
    global tor_proc
    # Kill managed process
    if tor_proc and tor_proc.poll() is None:
        tor_proc.terminate()
        try:
            tor_proc.wait(timeout=5)
        except:
            tor_proc.kill()
        tor_proc = None

    # Kill any process occupying our ports (orphaned Tor, etc.)
    for port in [SOCKS_PORT, CTRL_PORT]:
        try:
            subprocess.run(["fuser", "-k", f"{port}/tcp"],
                         capture_output=True, timeout=5)
        except:
            pass
    time.sleep(1)

def _parse_bootstrap_progress() -> int:
    """Lê o log do Tor e extrai a porcentagem de bootstrap."""
    try:
        if not LOG_FILE.exists():
            return 0
        content = LOG_FILE.read_text(errors="ignore")
        matches = re.findall(r"Bootstrapped (\d+)%", content)
        if matches:
            return int(matches[-1])
    except:
        pass
    return 0

def _wait_bootstrap(timeout: int = 90) -> bool:
    """Barra de progresso animada acompanhando o bootstrap real do Tor."""
    start = time.time()
    last = -1
    phases = [
        (0,   "conectando na rede Tor..."),
        (10,  "negociando com relays..."),
        (30,  "baixando consenso da rede..."),
        (50,  "construindo circuitos..."),
        (80,  "estabelecendo circuito..."),
        (95,  "finalizando..."),
        (100, "pronto!"),
    ]
    while time.time() - start < timeout:
        pct = _parse_bootstrap_progress()
        if pct != last:
            last = pct
            msg = next((m for lim, m in reversed(phases) if pct >= lim), "")
            if IS_TTY:
                progress_bar(pct, msg)
            time.sleep(0.15)
        else:
            time.sleep(0.25)
        if pct >= 100:
            if IS_TTY:
                progress_bar(100, "pronto!")
                print()
            return True
        # Process died?
        if tor_proc and tor_proc.poll() is not None:
            clear_line()
            return False
    clear_line()
    return False

def start_tor(quiet: bool = False) -> bool:
    global tor_proc, tor_started_by_us
    if tor_proc and tor_proc.poll() is None:
        return True

    # Check if OUR Tor is already running on the alternative ports
    our_socks = check_port("127.0.0.1", SOCKS_PORT)
    our_ctrl  = check_port("127.0.0.1", CTRL_PORT)

    if our_socks and our_ctrl and tor_proc and tor_proc.poll() is None:
        if not quiet:
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

    # Limpa log antigo para o bootstrap começar do zero
    try:
        LOG_FILE.unlink(missing_ok=True)
    except:
        pass

    info(f"Iniciando Tor {GRAY}(SOCKS5 :{SOCKS_PORT} · Control :{CTRL_PORT}){RESET}" if IS_TTY else "Iniciando Tor...")
    try:
        tor_proc = subprocess.Popen(
            [tor_bin, "-f", str(TORRC)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not _wait_bootstrap():
            err("Tor falhou ao iniciar (timeout no bootstrap).")
            return False
        tor_started_by_us = True
        ok(f"Tor conectado {GRAY}— circuito estabelecido{RESET}" if IS_TTY else "Tor conectado!")
        return True
    except Exception as e:
        err(f"Erro ao iniciar Tor: {e}")
        return False

def send_newnym(animated: bool = True) -> bool:
    try:
        import socket

        def _do():
            s = socket.create_connection(("127.0.0.1", CTRL_PORT), timeout=5)
            s.sendall(b"AUTHENTICATE\r\n")
            s.recv(1024)
            s.sendall(b"SIGNAL NEWNYM\r\n")
            s.recv(1024)
            s.close()

        if animated and IS_TTY:
            with Spinner("Rotacionando circuito (NEWNYM)..."):
                _do()
                time.sleep(1.5)
        else:
            _do()
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
    section("Adicionar App")
    c("  Como adicionar o app?", color=CYAN)
    c(f"  {MAGENTA}[1]{RESET} Selecionar com janela (zenity/kdialog)" if IS_TTY else "  [1] Selecionar com janela (zenity/kdialog)")
    c(f"  {MAGENTA}[2]{RESET} Digitar o caminho manualmente" if IS_TTY else "  [2] Digitar o caminho manualmente")
    c(f"  {GRAY}[0] Voltar{RESET}")
    c("")
    choice = input(f"  {BOLD}❯{RESET} " if IS_TTY else "  > ").strip()

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
        path = input(f"  {BOLD}❯{RESET} " if IS_TTY else "  > ").strip()
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
def section(title: str):
    """Título de seção estilizado."""
    c("")
    if IS_TTY:
        c(f"  {gradient_text('── ' + title.upper() + ' ' + '─' * max(40 - len(title), 0))}")
    else:
        c(f"  == {title} ==")
    c("")

def logo(animated: bool = False):
    if IS_TTY:
        os.system("clear")
    print_banner(animated=animated)
    c("")
    draw_status_bar()
    c("")

def menu_item(key: str, title: str, desc: str, color=CYAN):
    if IS_TTY:
        c(f"  {MAGENTA}{BOLD}[{key}]{RESET} {BOLD}{WHITE}{title}{RESET}")
        c(f"       {GRAY}{desc}{RESET}")
    else:
        c(f"  [{key}] {title} — {desc}")

def draw_menu():
    logo()
    if IS_TTY:
        c(f"  {gradient_text('╭' + '─' * 44 + '╮')}")
        c(f"  {gradient_text('│')}{BOLD}              M E N U                   {RESET}{gradient_text('│')}")
        c(f"  {gradient_text('╰' + '─' * 44 + '╯')}")
    c("")
    menu_item("1", "Rodar Torify", "Inicia Tor, rotaciona IP e verifica")
    menu_item("2", "Conferir IP", "Mostra IP real vs IP do Tor")
    menu_item("3", "Configurar", "Define o app padrão")
    menu_item("4", "Adicionar App", "Seleciona um binário/AppImage")
    menu_item("5", "Abrir App com Tor", "Lista apps salvos e abre com torsocks")
    menu_item("00", "Parar Tor", "Mata o Tor e restaura IP normal", color=RED)
    menu_item("0", "Sair", "Encerra o Torify")
    c("")
    return input(f"  {BOLD}{gradient_text('torify')} {MAGENTA}❯{RESET} " if IS_TTY else "  > ").strip()


# ── IP comparison panel ────────────────────────────────────────────────
def show_ip_panel(real: str, tor_ip: str):
    """Painel lado a lado com os IPs, estilizado."""
    if IS_TTY:
        line = gradient_text('─' * 46)
        c(f"  {line}")
        c(f"  {GRAY}IP real (sem Tor){RESET}   {BOLD}{YELLOW}{real}{RESET}")
        c(f"  {GRAY}IP pelo Tor      {RESET}   {BOLD}{GREEN}{tor_ip}{RESET}")
        c(f"  {line}")
    else:
        c(f"  IP real (sem Tor): {real}")
        c(f"  IP pelo Tor:       {tor_ip}")


# ── Options ────────────────────────────────────────────────────────────
def option_torify():
    logo()
    section("Rodar Torify")
    if not start_tor():
        input(f"\n  {GRAY}Pressione Enter para continuar...{RESET}" if IS_TTY else "  Pressione Enter...")
        return
    send_newnym()
    time.sleep(1)
    ok("IP rotacionado!")
    c("")

    spin = Spinner("Verificando IPs (real vs Tor)...")
    spin.__enter__()
    real = get_ip(use_tor=False)
    tor_ip = get_ip(use_tor=True)
    spin.__exit__()

    show_ip_panel(real, tor_ip)
    c("")

    if real and tor_ip and real != tor_ip and real != "?" and tor_ip != "?":
        ok("Proxy funcionando! IPs diferentes — você está anônimo.")
    elif real and tor_ip and real == tor_ip:
        warn("IPs iguais — verifique se o Tor está rodando.")
    else:
        warn("Não foi possível verificar (sem conexão?).")
    c("")

def option_check_ip():
    logo()
    section("Conferir IP")
    spin = Spinner("Consultando IP real...")
    spin.__enter__()
    real = get_ip(use_tor=False)
    spin.__exit__()

    tor_running = check_port("127.0.0.1", SOCKS_PORT, timeout=0.5)
    if tor_running:
        spin = Spinner("Consultando IP via Tor (SOCKS5)...")
        spin.__enter__()
        tor_ip = get_ip(use_tor=True)
        spin.__exit__()
    else:
        tor_ip = "Tor parado"
        warn("Tor não está rodando — use a opção [1] primeiro.")

    c("")
    show_ip_panel(real, tor_ip)
    c("")

    if tor_running:
        if real and tor_ip and real != tor_ip and tor_ip != "?":
            ok("Tor está funcionando!")
        elif real and tor_ip and real == tor_ip:
            err("Tor NÃO está roteando o tráfego.")
        else:
            err("Não foi possível verificar os IPs.")
    c("")

def option_config():
    logo()
    section("Configurar")
    apps = load_apps()
    auto = find_target_app()
    if auto:
        c(f"  {GRAY}Detectado automaticamente:{RESET} {GREEN}{auto}{RESET}" if IS_TTY else f"  Detectado: {auto}")
    elif apps:
        c(f"  {GRAY}Último app configurado:{RESET} {GREEN}{apps[-1]['path']}{RESET}" if IS_TTY else f"  Último: {apps[-1]['path']}")
    else:
        c("  Nenhum caminho configurado.", color=GRAY)
    c("")
    c("  Digite o caminho completo do executável")
    c("  (Enter para manter, 'auto' para detectar, 'reset' para limpar):", color=GRAY)
    c("")
    path = input(f"  {BOLD}❯{RESET} " if IS_TTY else "  > ").strip()

    if path == "":
        return
    elif path.lower() == "auto":
        with Spinner("Detectando apps instalados..."):
            time.sleep(0.8)
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
        logo()
        err("Nenhum app configurado. Use a opção 4 primeiro.")
        return

    logo()
    section("Abrir App com Tor")
    for i, app in enumerate(apps, 1):
        if IS_TTY:
            c(f"  {MAGENTA}{BOLD}[{i}]{RESET} {BOLD}{app['name']}{RESET}")
            c(f"      {GRAY}{app['path']}{RESET}")
        else:
            c(f"  [{i}] {app['name']} — {app['path']}")

    c(f"\n  {GRAY}[0] Voltar{RESET}")
    c("")
    choice = input(f"  {BOLD}❯{RESET} " if IS_TTY else "  > ").strip()
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

    c("")
    info(f"Abrindo '{app['name']}' com Tor...")
    c(f"      {GRAY}TORSOCKS_CONF_FILE={TORSOCKS_CONF} {ts} {app['path']}{RESET}" if IS_TTY else f"  torsocks {app['path']}")
    c("")

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
    section("Parar Tor")
    if not tor_proc or tor_proc.poll() is not None:
        info("Tor do Torify não está rodando.")
        c("")
        return

    with Spinner("Parando Tor do Torify..."):
        kill_our_tor()
        time.sleep(0.5)
    tor_started_by_us = False
    ok("Tor parado. Tráfego não passa mais pelo Torify.")
    c("  IP real restaurado.", color=GRAY)
    c("")

def option_add_app():
    logo()
    add_app_interactive()


# ── CLI ────────────────────────────────────────────────────────────────
def cli_install():
    """Install all dependencies and exit."""
    print_banner(animated=True)
    c("")
    section("Instalação completa")
    result = install_all_deps(cmdline=True)
    c("")
    sys.exit(0 if result else 1)

def cli_tor():
    """Start Tor, show IP, and exit."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    print_banner(animated=False)
    c("")
    if not MARKER.exists():
        auto_setup()
    if start_tor():
        send_newnym()
        time.sleep(1)
        spin = Spinner("Verificando IPs...")
        spin.__enter__()
        real = get_ip(use_tor=False)
        tor_ip = get_ip(use_tor=True)
        spin.__exit__()
        show_ip_panel(real, tor_ip)
        c("")
        sys.exit(0)
    sys.exit(1)


HELP_TEXT = """
Uso: torify [OPÇÃO]

Opções:
  --install, -i    Instala todas as dependências do sistema
  --tor, -t        Inicia Tor e mostra IP real vs IP pelo Tor
  --help, -h       Mostra esta ajuda

Sem argumentos: modo interativo (menu animado)
"""

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
            print_banner(animated=False)
            c(HELP_TEXT)
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
            c("")
            typewriter(gradient_text("  Até mais! Fique anônimo. ◆") if IS_TTY else "  Até mais!", delay=0.02)
            c("")
            kill_our_tor()
            sys.exit(0)
        else:
            err("Opção inválida.")
            time.sleep(0.8)
            continue

        input(f"  {GRAY}Pressione Enter para continuar...{RESET}" if IS_TTY else "  Pressione Enter...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        c("")
        c(gradient_text("  Até mais! Fique anônimo. ◆") if IS_TTY else "  Até mais!")
        c("")
        kill_our_tor()
        sys.exit(0)
    except Exception as e:
        err(f"Erro: {e}")
        sys.exit(1)
