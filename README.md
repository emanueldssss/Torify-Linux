# Torify v1.1 — Linux

Roteie qualquer aplicativo Linux pelo Tor com um clique.

![Torify Linux](screenshot.png)

## Como funciona

- **Tor** — daemon rodando na porta SOCKS5 `127.0.0.1:9050`
- **torsocks** — wrapper nativo do Tor que redireciona o tráfego via `LD_PRELOAD`
- **Menu interativo** — controle tudo pelo terminal
- **CLI** — comandos diretos sem menu

## Instalação rápida

### Binário (recomendado)

Baixe o binário compilado da [página de releases](https://github.com/emanueldssss/Torify-Linux/releases):

```bash
# Baixa o binário
wget https://github.com/emanueldssss/Torify-Linux/releases/download/v1.1.0/torify-linux-x86_64 -O torify
chmod +x torify

# Instala TUDO (tor, torsocks, curl, wget, etc)
./torify --install

# Roda
./torify
```

### Código fonte

```bash
git clone https://github.com/emanueldssss/Torify-Linux.git
cd Torify-Linux
chmod +x torify.py

# Instala TUDO (python3, tor, torsocks, curl, wget, etc)
python3 torify.py --install

# Ou apenas roda — instala automático na primeira execução
python3 torify.py
```

Na primeira execução, o script instala **todas as dependências** automaticamente:
1. **Python 3** (se não estiver instalado)
2. **Tor** — via pacote da distro ou Expert Bundle
3. **torsocks** — via pacote da distro
4. **curl/wget** — para verificação de IP
5. **zenity/xterm** — para interface opcional

> Nada de `sudo apt install` manual. O script faz tudo sozinho.

## CLI (command line)

```bash
python3 torify.py --install    # Instala todas as dependências e sai
python3 torify.py --tor        # Inicia Tor e mostra o IP
python3 torify.py --help       # Mostra ajuda
python3 torify.py              # Modo interativo (menu)
```

## Menu

```
  ========================
    Torify v1.1 — Linux
  ========================
  Tor + torsocks for Linux
  ========================
  Roteie qualquer app Linux
  pelo Tor com um clique.
  ========================

  [1] Rodar Torify
      Inicia Tor, rotaciona IP e mostra IP real vs Tor

  [2] Conferir IP
      Mostra IP real vs IP do Tor (com verificação real via SOCKS5)

  [3] Configurar
      Define o app padrão

  [4] Adicionar App
      Seleciona um binário/AppImage

  [5] Abrir App com Tor
      Lista apps salvos e abre com torsocks

  [0] Sair
```

### Opção 1 — Rodar Torify

Inicia o Tor (se não estiver rodando), rotaciona o IP via `NEWNYM` e mostra:
- Seu IP real (sem Tor)
- Seu IP pelo Tor

### Opção 2 — Conferir IP

Mostra os dois IPs lado a lado e confirma se o proxy está funcionando.

### Opção 3 — Configurar

Define manualmente o caminho do executável que será aberto com Tor.
- Digite o caminho completo
- `auto` — tenta detectar automaticamente (discord, firefox, telegram, etc.)
- `reset` — limpa a configuração

### Opção 4 — Adicionar App

Adiciona um aplicativo à lista de salvos:
- Usa `zenity` ou `kdialog` para abrir um seletor de arquivos
- Se nenhum diálogo estiver disponível, permite digitar o caminho manualmente
- O app fica salvo em `~/.config/torify/apps.txt`

### Opção 5 — Abrir App com Tor

Lista todos os apps salvos. Escolha um número e o script:
1. Inicia o Tor (se necessário)
2. Roda o app via `torsocks <app>`

## Dependências

### Gerenciamento automático

O script instala **todas as dependências** sozinho:
- `python3` — intérprete
- `tor` — daemon de anonimização
- `torsocks` — wrapper LD_PRELOAD nativo do Tor
- `curl` / `wget` — verificação de IP
- `zenity` / `xterm` — interface opcional

Use `python3 torify.py --install` para instalar tudo de uma vez.

## Estrutura de arquivos

```
~/.config/torify/
├── tor/                 # Tor Expert Bundle (se baixado automaticamente)
│   └── tor              # binário do Tor
├── torrc                # configuração do Tor
├── torsocks.conf        # configuração do torsocks
├── apps.txt             # lista de apps salvos
└── .setup-complete      # marcador de setup concluído
```

## Exemplo de uso

```bash
# 1. Instalar dependências
python3 torify.py --install

# 2. Rodar modo interativo
python3 torify.py

# 3. Adicione um app (opção 4) — selecione o Discord, Firefox, etc.

# 4. Abra o app com Tor (opção 5) — escolha o número do app
```

## Compatível com

- **Debian/Ubuntu** — `apt`
- **Fedora/CentOS** — `dnf`
- **Arch Linux** — `pacman`
- **openSUSE** — `zypper`
- **Alpine** — `apk`
- Qualquer distro com Python 3.6+

## Licença

MIT
