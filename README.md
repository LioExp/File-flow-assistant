# FileFlow

> [Portugues](README.pt.md) | English🇺🇸

Intelligent file organizer that monitors folders, detects duplicates, and keeps your files safe.

## Features

- **Real-time monitoring** — watches folders and reacts to file changes
- **Duplicate detection** — SHA-256 hashing, generates reports (never deletes automatically)
- **Soft delete** — deleted files go to hidden trash (`~/.fileflow_trash`), recoverable for 30 days
- **Auto organization** — moves inactive files by type/extension/keyword
- **Virus scanning** — integrates with ClamAV (Linux) or Windows Defender
- **Daemon mode** — runs in background, persists after terminal close
- **MCP server** — AI integration via Model Context Protocol

## Install

```bash
git clone https://github.com/LioExp/File-flow-assistant.git
cd File-flow-assistant
pip install -r requirements.txt
```

## Usage

```bash
# Dashboard
fileflow

# Start monitoring
fileflow start

# Start as daemon (background)
fileflow start --daemon

# Scan for duplicates
fileflow scan

# Organize files
fileflow organize

# View trash
fileflow trash
```

## Commands

| Command | Description |
|---------|-------------|
| `fileflow` | Show dashboard |
| `fileflow start` | Start monitoring |
| `fileflow start --daemon` | Start in background |
| `fileflow stop` | Stop daemon |
| `fileflow scan` | Scan for duplicates |
| `fileflow organize` | Organize inactive files |
| `fileflow trash` | View trash |
| `fileflow recover <file>` | Recover from trash |
| `fileflow status` | Show dashboard |
| `fileflow watch-add <dir>` | Add directory to monitor |
| `fileflow rules-add` | Add organization rule |
| `fileflow scanfile <file>` | Scan file for malware |

## MCP Integration

```bash
# Enable MCP
fileflow mcp-enable

# Start with MCP
fileflow start --mcp
```

## Tech Stack

- Python 3.8+
- watchdog (file monitoring)
- SQLite (index storage)
- Rich (terminal UI)
- MCP SDK (AI integration)
