# Torify v1.0 — Linux

Roteie qualquer aplicativo Linux pelo Tor com um clique.

![Torify Linux](screenshot.png)

## Como funciona

- **Tor** — daemon rodando nas portas **9052** (SOCKS5) e **9053** (Control)
- **torsocks** — wrapper nativo do Tor que redireciona o tráfego via `LD_PRELOAD`
- **Menu interativo** — controle tudo pelo terminal
- **CLI** — comandos diretos sem menu

> ⚠️ Usa portas **alternativas** (9052/9053) para não conflitar com o Tor do sistema (porta 9050).

---

## Índice

- [Instalação](#instalação)
  - [Binário (recomendado)](#binário-recomendado)
  - [Código fonte](#código-fonte)
- [Primeira execução](#primeira-execução)
- [Guia de uso](#guia-de-uso)
  - [Menu interativo](#menu-interativo)
  - [CLI](#cli-command-line)
  - [Fluxo completo](#fluxo-completo)
  - [Opções detalhadas](#opções-detalhadas)
- [Estrutura de arquivos](#estrutura-de-arquivos)
- [Compatibilidade](#compatibilidade)

---

## Instalação

### Binário (recomendado)

Baixe o executável compilado da [página de releases](https://github.com/emanueldssss/Torify-Linux/releases) — não precisa de Python instalado.

```bash
# 1. Baixa o binário
wget https://github.com/emanueldssss/Torify-Linux/releases/download/v1.0.0/torify-linux-x86_64 -O torify

# 2. Dá permissão de execução
chmod +x torify

# 3. Instala dependências (tor, torsocks, curl, etc)
./torify --install

# 4. Executa
./torify
```

### Código fonte

Requer **Python 3.6+** e `git`.

```bash
# 1. Clona o repositório
git clone https://github.com/emanueldssss/Torify-Linux.git
cd Torify-Linux

# 2. Dá permissão
chmod +x torify.py

# 3. Instala dependências
python3 torify.py --install

# 4. Executa
python3 torify.py
```

---

## Primeira execução

Na primeira execução, o Torify faz tudo automático:

1. Detecta sua distribuição (Debian, Fedora, Arch, openSUSE, Alpine)
2. Instala **Tor** — via pacote da distro ou Expert Bundle
3. Instala **torsocks** — wrapper oficial do Tor Project
4. Instala **curl/wget** — para verificação de IP
5. Cria as configurações em `~/.config/torify/`
6. Inicia o menu interativo

> Nada de `sudo apt install` manual. O script faz tudo sozinho.

---

## Guia de uso

### CLI (command line)

```bash
./torify --install        # Instala dependências e sai
./torify --tor            # Inicia Tor e mostra IP real vs IP do Tor
./torify --help           # Mostra ajuda
./torify                  # Modo interativo (menu)
```

### Menu interativo

```
  ========================
    Torify v1.0 — Linux
  ========================
  Tor + torsocks for Linux
  ========================
  Roteie qualquer app Linux
  pelo Tor com um clique.
  ========================

  [1]  Rodar Torify
       Inicia Tor, rotaciona IP e mostra IP real vs Tor

  [2]  Conferir IP
       Mostra IP real vs IP do Tor (verificação real via SOCKS5)

  [3]  Configurar
       Define o caminho do app padrão

  [4]  Adicionar App
       Seleciona um binário/AppImage para salvar

  [5]  Abrir App com Tor
       Lista apps salvos e abre com torsocks

  [00] Parar Tor
       Mata o Tor do Torify e restaura o IP normal

  [0]  Sair
```

### Fluxo completo

```bash
# Instala
wget https://github.com/emanueldssss/Torify-Linux/releases/download/v1.0.0/torify-linux-x86_64 -O torify
chmod +x torify
./torify --install

# Roda o menu
./torify

# --- Dentro do menu ---

# [1] Rodar Torify
#   → Tor inicia na porta 9052
#   → IP rotacionado (NEWNYM)
#   → Mostra:
#       IP real (sem Tor): 191.5.234.6
#       IP pelo Tor:        171.25.193.38
#   → Proxy funcionando! IPs diferentes.

# [4] Adicionar App
#   → Escolhe: digitar caminho
#   → Digita: /usr/bin/firefox
#   → 'firefox' adicionado!

# [5] Abrir App com Tor
#   → [1] firefox
#   → Escolhe 1
#   → Firefox abre roteado pelo Tor

# [2] Conferir IP
#   → Verifica se o Tor está funcionando

# [00] Parar Tor
#   → Mata o Tor
#   → IP real restaurado
#   → Tráfego volta ao normal

# [0] Sair
```

### ⚠️ Entendendo os IPs do Tor

É **normal** o IP do Tor mudar toda hora. A rede Tor tem milhares de nós de saída espalhados pelo mundo. Cada requisição sua pode sair por um nó diferente:

```
[1] Rodar Torify → IP Tor: 23.191.200.5
[2] Conferir IP  → IP Tor: 104.244.73.43
[2] de novo      → IP Tor: 171.25.193.38
```

todos são IPs **válidos da rede Tor**. Se aparecesse o **mesmo** IP sempre, aí seria preocupante — significaria que o tráfego **não** está passando pelo Tor de verdade.

O que importa é: **IP real ≠ IP do Tor**. Se são diferentes, o Torify está funcionando.

### Opções detalhadas

#### [1] Rodar Torify

Inicia o Tor do Torify (porta 9052), rotaciona o IP via `SIGNAL NEWNYM` na porta de controle 9053 e mostra:
- **IP real** — seu IP sem Tor (requisição direta via curl)
- **IP pelo Tor** — seu IP através do Tor (requisição via `curl --socks5 127.0.0.1:9052`)
- Se os IPs forem diferentes ✅ o proxy está funcionando

#### [2] Conferir IP

Mostra os dois IPs lado a lado para verificar se o Tor está ativo.

#### [3] Configurar

Define manualmente o executável que será aberto com Tor:
- Digite o caminho completo (ex: `/usr/bin/firefox`)
- `auto` — detecta automaticamente (discord, firefox, telegram, etc.)
- `reset` — limpa a configuração

#### [4] Adicionar App

Adiciona um aplicativo à lista de salvos:
- Opção 1 — usa `zenity` ou `kdialog` (seletor de arquivos gráfico)
- Opção 2 — digita o caminho manualmente
- Fica salvo em `~/.config/torify/apps.txt`

#### [5] Abrir App com Tor

Lista os apps salvos. Escolha um número e o Torify:
1. Inicia o Tor (se necessário)
2. Abre o app via `torsocks <app>` com `TORSOCKS_CONF_FILE` apontando para a porta 9052

#### [00] Parar Tor

Mata o processo do Tor gerenciado pelo Torify. O tráfego volta a sair pelo IP real imediatamente.

#### [0] Sair

Encerra o programa e mata o Tor do Torify (se estiver rodando).

---

## Estrutura de arquivos

```
~/.config/torify/
├── tor/                 # Tor Expert Bundle (se baixado automaticamente)
│   └── tor              # binário do Tor
├── torrc                # configuração do Tor (portas 9052/9053)
├── torsocks.conf        # configuração do torsocks (porta 9052)
├── apps.txt             # lista de apps salvos
└── .setup-complete      # marcador de setup concluído
```

---

## Compatibilidade

| Distribuição | Gerenciador | Pacotes |
|:---|:---|:---|
| Debian / Ubuntu | `apt` | `tor torsocks curl wget` |
| Fedora / CentOS | `dnf` | `tor torsocks curl wget` |
| Arch Linux | `pacman` | `tor torsocks curl wget` |
| openSUSE | `zypper` | `tor torsocks curl wget` |
| Alpine | `apk` | `tor torsocks curl wget` |

> Qualquer distribuição com Python 3.6+ e `sudo`.

---

## Licença

MIT
