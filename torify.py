#!/usr/bin/env python3
"""
Torify — Linux
Roteie qualquer aplicativo Linux pelo Tor com um clique.
"""

import os, sys, subprocess, shutil, time, json, textwrap, glob, signal
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR  = Path.home() / ".config" / "torify"
TOR_DIR   = BASE_DIR / "tor"
APPS_FILE = BASE_DIR / "apps.txt"
TORRC     = BASE_DIR / "torrc"
PROXYCONF = BASE_DIR / "proxychains.conf"
MARKER    = BASE_DIR / ".setup-complete"
VENV_DIR  = BASE_DIR / "venv"

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


# ── Helpers ────────────────────────────────────────────────────────────
def c(*args, color="", bold=False, sep=" "):
    text = sep.join(str(a) for a in args)
    if bold:   text = f"{BOLD}{text}{RESET}"
    if color:  text = f"{color}{text}{RESET}"
    print(text)

def err(msg): c(f"[!] {msg}", color=RED)

def ok(msg):  c(f"[+] {msg}", color=GREEN)

def info(msg): c(f"[*] {msg}", color=CYAN)


# ── Setup ──────────────────────────────────────────────────────────────
def detect_distro() -> str:
    """Detect package-manager family."""
    if shutil.which("apt-get"):  return "debian"
    if shutil.which("dnf"):      return "fedora"
    if shutil.which("yum"):      return "fedora"
    if shutil.which("pacman"):   return "arch"
    if shutil.which("zypper"):   return "suse"
    if shutil.which("apk"):      return "alpine"
    return "unknown"

def install_pkg(pkg: str) -> bool:
    """Install a system package using the detected package manager."""
    distro = detect_distro()
    sudo = shutil.which("sudo")
    if not sudo:
        err("sudo não encontrado. Instale manualmente ou execute como root.")
        return False

    cmds = {
        "debian": ["apt-get", "install", "-y"],
        "fedora": ["dnf", "install", "-y"],
        "arch":   ["pacman", "-S", "--noconfirm"],
        "suse":   ["zypper", "install", "-y"],
        "alpine": ["apk", "add"],
    }
    cmd = cmds.get(distro)
    if not cmd:
        err(f"Distro não reconhecida ({distro}). Instale '{pkg}' manualmente.")
        return False

    try:
        subprocess.run([sudo, *cmd, pkg], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def check_tool(name: str, pkg: str = None) -> str | None:
    """Find a binary; optionally install it via package manager."""
    path = shutil.which(name)
    if path:
        return path
    c(f"  [!] '{name}' não encontrado.", color=YELLOW)
    if pkg:
        c(f"  [*] Tentando instalar '{pkg}' via pacote...", color=CYAN)
        if install_pkg(pkg) and (path := shutil.which(name)):
            return path
    return None

def write_configs():
    """Write Tor and proxychains config files."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # torrc
    TORRC.write_text(textwrap.dedent("""\
        SocksPort 9050
        ControlPort 9051
        CookieAuthentication 0
        Log notice file /dev/null
    """).lstrip())

    # proxychains.conf
    PROXYCONF.write_text(textwrap.dedent("""\
        strict_chain
        proxy_dns
        tcp_read_time_out 15000
        tcp_connect_time_out 8000
        [ProxyList]
        socks5 127.0.0.1 9050
    """).lstrip())

    ok("Configurações criadas em ~/.config/torify/")

def download_tor_expert() -> Path | None:
    """Download Tor Expert Bundle for Linux and return path to binary."""
    import urllib.request, tarfile

    arch_map = {"x86_64": "x86_64", "i686": "i686", "aarch64": "aarch64"}
    arch = arch_map.get(os.uname().machine, "x86_64")
    url = (f"https://www.torproject.org/dist/torbrowser/"
           f"15.0.18/tor-expert-bundle-linux-{arch}-15.0.18.tar.gz")

    dest = BASE_DIR / "tor-dl.tar.gz"
    info(f"Baixando Tor Expert Bundle ({arch})...")

    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as e:
        err(f"Falha no download: {e}")
        return None

    info("Extraindo...")
    tarball = BASE_DIR / "tor"
    tarball.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest) as tf:
        tf.extractall(path=tarball)
    dest.unlink()

    # find tor binary
    tor_bin = next(tarball.rglob("tor"), None)
    if tor_bin and tor_bin.is_file():
        tor_bin.chmod(0o755)
        ok(f"Tor baixado: {tor_bin}")
        return tor_bin
    err("Binário do Tor não encontrado após extração.")
    return None

def run_setup():
    """First-run setup – install dependencies."""
    c("", color=MAGENTA)
    c("  ========================", bold=True)
    c("    Primeira Execução", bold=True)
    c("  ========================", bold=True)
    c("")
    c("  Verificando dependências...\n", color=CYAN)

    # ── Tor ──
    tor_path = shutil.which("tor")
    if not tor_path:
        c("  [1/2] Tor não encontrado. Tentando baixar Expert Bundle...", color=YELLOW)
        tor_path = download_tor_expert()
        if not tor_path:
            c("  [*] Tentando instalar via pacote (pode pedir sudo)...", color=CYAN)
            if install_pkg("tor"):
                tor_path = shutil.which("tor")
    if tor_path:
        ok(f"Tor: {tor_path}")
    else:
        err("Tor não disponível. Instale manualmente: apt install tor")
        c("  [!] Opções 1 e 2 não funcionarão sem Tor.", color=YELLOW)

    # ── Proxychains ──
    px_names = ["proxychains4", "proxychains"]
    px_path = None
    for n in px_names:
        px_path = shutil.which(n)
        if px_path: break

    if not px_path:
        c("  [2/2] Proxychains não encontrado. Tentando instalar...", color=YELLOW)
        if install_pkg("proxychains4") or install_pkg("proxychains-ng"):
            for n in px_names:
                px_path = shutil.which(n)
                if px_path: break
    if px_path:
        ok(f"Proxychains: {px_path}")
    else:
        c("  [!] Proxychains não disponível. Opção 5 não funcionará.", color=YELLOW)
        c("      Instale manualmente: sudo apt install proxychains4", color=GRAY)

    # ── Configs ──
    write_configs()
    MARKER.write_text("setup complete")
    ok("Setup concluído!")
    c("")


# ── Tor management ─────────────────────────────────────────────────────
def start_tor():
    """Start Tor daemon with our config."""
    global tor_proc

    if tor_proc and tor_proc.poll() is None:
        return  # already running

    tor_bin = shutil.which("tor")
    if not tor_bin:
        # try expert bundle
        tor_bin = next((TOR_DIR.rglob("tor")), None)
        if not tor_bin:
            err("Tor não encontrado. Rode o setup primeiro (opção 3).")
            return False
        tor_bin = str(tor_bin)

    info("Iniciando Tor...")
    try:
        tor_proc = subprocess.Popen(
            [tor_bin, "-f", str(TORRC)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
        if tor_proc.poll() is not None:
            err("Tor falhou ao iniciar.")
            return False
        ok("Tor rodando (SOCKS5 :9050)")
        return True
    except Exception as e:
        err(f"Erro ao iniciar Tor: {e}")
        return False

def send_newnym():
    """Send NEWNYM signal to Tor control port."""
    try:
        import socket
        s = socket.create_connection(("127.0.0.1", 9051), timeout=5)
        s.sendall(b"AUTHENTICATE\r\n")
        s.recv(1024)
        s.sendall(b"SIGNAL NEWNYM\r\n")
        s.recv(1024)
        s.close()
        return True
    except Exception as e:
        err(f"Falha ao rotacionar IP: {e}")
        return False

def get_ip(url="https://api.ipify.org") -> str:
    """Fetch public IP via curl or wget."""
    for cmd in [["curl", "-s", "--max-time", "5"],
                ["wget", "-qO-", "--timeout=5"]]:
        try:
            r = subprocess.run([*cmd, url], capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except: continue
    return "?"


# ── Proxychains ────────────────────────────────────────────────────────
def get_proxychains_bin() -> str | None:
    for n in ["proxychains4", "proxychains"]:
        p = shutil.which(n)
        if p: return p
    return None


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
    """Auto-detect a common app to proxy."""
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
    """Add an app via file dialog or manual entry."""
    apps = load_apps()

    c("\n  Como adicionar o app?", color=CYAN)
    c("  1) Selecionar com janela (zenity/kdialog)")
    c("  2) Digitar o caminho manualmente")
    c("  0) Voltar")
    c("")

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
    c("    Torify v1.0 — Linux", color=MAGENTA, bold=True)
    c("  ========================", color=MAGENTA, bold=True)
    c("  Tor + Proxychains for Linux", color=GRAY)
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
    c("      Seleciona um .exe/.AppImage/bin\n")
    c("  [5] Abrir App com Tor", color=CYAN)
    c("      Lista apps salvos e abre com proxychains\n")
    c("  [0] Sair", color=CYAN)
    c("")
    return input("  > ").strip()


# ── Options ────────────────────────────────────────────────────────────
def option_torify():
    logo()
    info("Iniciando Torify...\n")
    if not start_tor():
        return
    info("Rotacionando IP...")
    send_newnym()
    time.sleep(2)
    ok("IP rotacionado!\n")

    real = get_ip()
    info(f"IP real (sem Tor): {real}")

    tor_ip = get_ip()
    c(f"IP pelo Tor:        {tor_ip}", color=GREEN)

    if real and tor_ip and real != tor_ip:
        c("\n  [+] Proxy funcionando! IPs diferentes.", color=GREEN)
    elif real and tor_ip:
        c("\n  [!] IPs iguais — verifique se o Tor está rodando.", color=YELLOW)
    c("")

def option_check_ip():
    logo()
    info("Verificando IPs...\n")
    real = get_ip()
    info(f"IP real (sem Tor): {real}")

    tor_ip = get_ip()
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

    c("")
    c("  Digite o caminho completo do executável")
    c("  (Enter para manter, 'auto' para detectar, 'reset' para limpar):", color=GRAY)
    path = input("\n  > ").strip()

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
    """List saved apps and launch one with proxychains."""
    apps = load_apps()
    if not apps:
        err("Nenhum app configurado. Use a opção 4 primeiro.")
        c("")
        return

    logo()
    c("  Apps salvos:\n", color=CYAN)
    for i, app in enumerate(apps, 1):
        c(f"  [{i}] {app['name']}", color=GREEN)
        c(f"      {app['path']}", color=GRAY)

    c("")
    c("  [0] Voltar", color=GRAY)
    c("")
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

    px = get_proxychains_bin()
    if not px:
        err("Proxychains não encontrado.")
        return

    c(f"\n  [*] Abrindo '{app['name']}' com Tor...", color=CYAN)
    c(f"      {px} -f {PROXYCONF} {app['path']}\n", color=GRAY)

    try:
        subprocess.Popen(
            [px, "-f", str(PROXYCONF), app["path"]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ok(f"'{app['name']}' iniciado com Tor!")
    except Exception as e:
        err(f"Erro ao iniciar: {e}")
    c("")

def option_add_app():
    logo()
    add_app_interactive()
    c("")


# ── Main ───────────────────────────────────────────────────────────────
def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    if not MARKER.exists():
        run_setup()
        if not MARKER.exists():
            err("Setup incompleto. Verifique as mensagens acima.")
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
        elif op == "0":
            c("\n  Até mais!\n", color=MAGENTA)
            if tor_proc and tor_proc.poll() is None:
                tor_proc.terminate()
            sys.exit(0)
        else:
            err("Opção inválida.\n")

        input("  Pressione Enter para continuar...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        c("\n  Até mais!\n", color=MAGENTA)
        if tor_proc and tor_proc.poll() is None:
            tor_proc.terminate()
        sys.exit(0)
    except Exception as e:
        err(f"Erro: {e}")
        sys.exit(1)
