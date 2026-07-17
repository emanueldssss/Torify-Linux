# Torify — Linux

Roteie qualquer aplicativo Linux pelo Tor com um clique.

![Torify Linux](screenshot.png)

## Como funciona

- **Tor** — daemon rodando na porta SOCKS5 `127.0.0.1:9050`
- **Proxychains-ng** — hook via `LD_PRELOAD` que redireciona o tráfego do app pelo Tor
- **Menu interativo** — controle tudo pelo terminal

## Instalação rápida

```bash
git clone https://github.com/emanueldssss/Torify-Linux.git
cd Torify-Linux
chmod +x torify.py
./torify.py
```

Na primeira execução, o script:
1. Verifica se `tor` e `proxychains4` estão instalados
2. Se não estiverem, baixa o **Tor Expert Bundle** automaticamente (sem precisar de sudo)
3. Se o proxychains não estiver instalado, tenta instalar via `apt`/`dnf`/`pacman` (pode pedir sudo)
4. Cria os arquivos de configuração em `~/.config/torify/`

> **Alternativa**: instale manualmente com `sudo apt install tor proxychains4` (Debian/Ubuntu)  
> Depois só rode `./torify.py` — o setup detecta que os pacotes já existem e pula a instalação.

## Menu

```
  ========================
    Torify v1.0 — Linux
  ========================
  Tor + Proxychains for Linux
  ========================

  [1] Rodar Torify
      Inicia Tor e rotaciona IP

  [2] Conferir IP
      Mostra IP real vs IP do Tor

  [3] Configurar
      Define o app padrão

  [4] Adicionar App
      Seleciona um binário/AppImage

  [5] Abrir App com Tor
      Lista apps salvos e abre com proxychains

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
2. Roda o app via `proxychains4 -f ~/.config/torify/proxychains.conf <app>`

## Dependências

### Essenciais (instaladas automaticamente)
- **Tor** — baixado como Expert Bundle (tarball) do torproject.org
- **Proxychains-ng** — instalado via pacote da distribuição (apt/dnf/pacman)

### Opcionais
- **zenity** ou **kdialog** — para o seletor de arquivos na opção 4
- **curl** ou **wget** — para verificar IP (geralmente já vem instalado)

## Estrutura de arquivos

```
~/.config/torify/
├── tor/                 # Tor Expert Bundle (se baixado automaticamente)
│   └── tor              # binário do Tor
├── torrc                # configuração do Tor
├── proxychains.conf     # configuração do proxychains
├── apps.txt             # lista de apps salvos
└── .setup-complete      # marcador de setup concluído
```

## Exemplo de uso

```bash
# 1. Rode o script
./torify.py

# 2. Na primeira vez, ele baixa as dependências automaticamente

# 3. Adicione um app (opção 4) — selecione o Discord, Firefox, etc.

# 4. Abra o app com Tor (opção 5) — escolha o número do app
```

## Compativel com

- **Debian/Ubuntu** — `apt`
- **Fedora/CentOS** — `dnf`
- **Arch Linux** — `pacman`
- **openSUSE** — `zypper`
- **Alpine** — `apk`
- Qualquer distro com Python 3.6+ e `bash`

## Licença

MIT
