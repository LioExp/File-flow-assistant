# FileFlow

> Portugues | [English](README.md)

Organizador inteligente de ficheiros que monitoriza pastas, deteta duplicados e mantém os teus ficheiros seguros.

## Funcionalidades

- **Monitoramento em tempo real** — observa pastas e reage a alterações
- **Deteção de duplicados** — hash SHA-256, gera relatórios (nunca apaga automaticamente)
- **Soft delete** — ficheiros apagados vão para lixeira oculta (`~/.fileflow_trash`), recuperáveis por 30 dias
- **Organização automática** — move ficheiros inativos por tipo/extensão/palavra-chave
- **Scanner de vírus** — integra com ClamAV (Linux) ou Windows Defender
- **Modo daemon** — corre em segundo plano, persiste após fechar terminal
- **Servidor MCP** — integração com IA via Model Context Protocol

## Instalação

```bash
git clone https://github.com/LioExp/File-flow-assistant.git
cd File-flow-assistant
pip install -r requirements.txt
```

## Uso

```bash
# Dashboard
fileflow

# Iniciar monitoramento
fileflow start

# Iniciar como daemon (segundo plano)
fileflow start --daemon

# Escanear duplicados
fileflow scan

# Organizar ficheiros
fileflow organize

# Ver lixeira
fileflow trash
```

## Comandos

| Comando | Descrição |
|---------|-----------|
| `fileflow` | Mostrar dashboard |
| `fileflow start` | Iniciar monitoramento |
| `fileflow start --daemon` | Iniciar em segundo plano |
| `fileflow stop` | Parar daemon |
| `fileflow scan` | Escanear duplicados |
| `fileflow organize` | Organizar ficheiros inativos |
| `fileflow trash` | Ver lixeira |
| `fileflow recover <ficheiro>` | Recuperar da lixeira |
| `fileflow status` | Mostrar dashboard |
| `fileflow watch-add <dir>` | Adicionar pasta para monitorar |
| `fileflow rules-add` | Adicionar regra de organização |
| `fileflow scanfile <ficheiro>` | Escanear ficheiro para vírus |

## Integração MCP

```bash
# Ativar MCP
fileflow mcp-enable

# Iniciar com MCP
fileflow start --mcp
```

## Stack

- Python 3.8+
- watchdog (monitoramento de ficheiros)
- SQLite (armazenamento do índice)
- Rich (UI de terminal)
- MCP SDK (integração com IA)
