# Torify v2.0 — Linux

Roteie qualquer aplicativo Linux pelo Tor com um clique — agora com **CLI animado** e **installer multiplataforma**.

```
████████╗ ██████╗ ██████╗ ██╗███████╗██╗   ██╗
╚══██╔══╝██╔═══██╗██╔══██╗██║██╔════╝╚██╗ ██╔╝
   ██║   ██║   ██║██████╔╝██║█████╗   ╚████╔╝ 
   ██║   ██║   ██║██╔══██╗██║██╔══╝    ╚██╔╝  
   ██║   ╚██████╔╝██║  ██║██║██║        ██║   
   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝        ╚═╝   
```

## Novidades da v2.0

- **CLI lindo e animado** — banner ASCII com gradiente roxo→cyan, spinners braille, efeito typewriter e painéis estilizados
- **Barra de progresso real do bootstrap do Tor** — acompanha o log do Tor e mostra `0% → 100%` com as fases da conexão ("negociando com relays...", "construindo circuitos...")
- **Installer inteligente** — detecta o sistema operacional (Linux, macOS, Windows/WSL) e a distribuição, e instala todos os componentes automaticamente
- **Status do Tor no menu** — indicador `●` verde/vermelho mostrando se o Tor está rodando
- **Painel de IPs lado a lado** — comparação visual do IP real vs IP do Tor

## Como funciona

- **Tor** — daemon rodando nas portas **9052** (SOCKS5) e **9053** (Control)
- **torsocks** — wrapper nativo do Tor que redireciona o tráfego via `LD_PRELOAD`
- **Menu interativo animado** — controle tudo pelo terminal
- **CLI** — comandos diretos sem menu

> ⚠️ Usa portas **alternativas** (9052/9053) para não conflitar com o Tor do sistema (porta 9050).

---

## Índice

- [Instalação](#instalação)
  - [Installer automático (recomendado)](#installer-automático-recomendado)
  - [Windows](#windows)
  - [Código fonte (manual)](#código-fonte-manual)
- [Guia de uso](#guia-de-uso)
- [Estrutura de arquivos](#estrutura-de-arquivos)
- [Compatibilidade](#compatibilidade)

---

## Instalação

### Installer automático (recomendado)

Um comando só — o installer **detecta seu sistema** (Linux/macOS/WSL + distro) e instala tudo:

```bash
curl -sSL https://raw.githubusercontent.com/emanueldssss/Torify-Linux/master/install.sh | bash
```

O que ele faz:

1. **Detecta o SO** — Linux, macOS ou Windows (Git Bash/WSL)
2. **Detecta a distro** — Debian/Ubuntu, Fedora, Arch, openSUSE ou Alpine
3. **Instala os componentes** — `python3`, `tor`, `torsocks`, `curl`, `wget` (via `apt`/`dnf`/`pacman`/`zypper`/`apk` ou Homebrew no macOS)
4. **Instala o comando `torify`** em `~/.local/bin` (e adiciona ao PATH)
5. **Verifica** se tudo ficou funcionando

Depois é só rodar:

```bash
torify
```

### Windows

O Torify roda dentro do **WSL**. No PowerShell como **Administrador**:

```powershell
irm https://raw.githubusercontent.com/emanueldssss/Torify-Linux/master/install.ps1 | iex
```

O installer verifica se o WSL existe (instala se necessário), e roda a instalação dentro da distro Linux. Depois:

```powershell
wsl torify
```

### Código fonte (manual)

Requer **Python 3.10+** e `git`.

```bash
git clone https://github.com/emanueldssss/Torify-Linux.git
cd Torify-Linux
bash install.sh        # ou: python3 torify.py --install
python3 torify.py
```

---

## Guia de uso

### CLI (command line)

```bash
torify --install        # Instala dependências e sai
torify --tor            # Inicia Tor (barra de bootstrap animada) e mostra IPs
torify --help           # Mostra ajuda
torify                  # Modo interativo (menu animado)
```

### Menu interativo

```
╭────────────────────────────────────────────╮
│              M E N U                       │
╰────────────────────────────────────────────╯

[1] Rodar Torify
     Inicia Tor, rotaciona IP e verifica
[2] Conferir IP
     Mostra IP real vs IP do Tor
[3] Configurar
     Define o app padrão
[4] Adicionar App
     Seleciona um binário/AppImage
[5] Abrir App com Tor
     Lista apps salvos e abre com torsocks
[00] Parar Tor
     Mata o Tor e restaura IP normal
[0] Sair

torify ❯
```

### Fluxo completo

```bash
# Instala com um comando
curl -sSL https://raw.githubusercontent.com/emanueldssss/Torify-Linux/master/install.sh | bash

# Abre o menu
torify

# [1] Rodar Torify
#   → Barra de progresso do bootstrap: ▓▓▓▓▓▓░░░░ 60% construindo circuitos...
#   → ✓ Tor conectado — circuito estabelecido
#   → IP real (sem Tor):  191.5.234.6
#   → IP pelo Tor:        171.25.193.38
#   → ✓ Proxy funcionando! IPs diferentes — você está anônimo.

# [4] Adicionar App  →  digita /usr/bin/firefox

# [5] Abrir App com Tor  →  Firefox abre roteado pelo Tor

# [00] Parar Tor  →  tráfego volta ao normal
```

---

## Estrutura de arquivos

```
~/.config/torify/
├── tor/                 # Tor Expert Bundle (se baixado automaticamente)
├── torrc                # configuração do Tor (portas 9052/9053)
├── torsocks.conf        # configuração do torsocks (porta 9052)
├── tor.log              # log do Tor (usado na barra de bootstrap)
├── apps.txt             # lista de apps salvos
└── .setup-complete      # marcador de setup concluído

~/.local/lib/torify/torify.py   # script principal (instalado pelo install.sh)
~/.local/bin/torify             # comando global
```

---

## Compatibilidade

| Sistema | Installer | Componentes |
|:---|:---|:---|
| Debian / Ubuntu | `install.sh` → `apt` | `python3 tor torsocks curl wget` |
| Fedora / CentOS | `install.sh` → `dnf` | `python3 tor torsocks curl wget` |
| Arch Linux | `install.sh` → `pacman` | `python tor torsocks curl wget` |
| openSUSE | `install.sh` → `zypper` | `python3 tor torsocks curl wget` |
| Alpine | `install.sh` → `apk` | `python3 tor torsocks curl wget` |
| macOS | `install.sh` → `brew` | `tor curl wget` (+ torsocks se disponível) |
| Windows | `install.ps1` → WSL | mesmos do Linux, dentro do WSL |

> O CLI funciona em qualquer terminal com suporte a ANSI. Sem TTY (pipes, CI), as animações são desativadas automaticamente. Respeita a variável `NO_COLOR`.

---

## Licença

MIT
