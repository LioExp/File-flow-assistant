import os
import json
from pathlib import Path
from config import FILEFLOW_HOME

MCP_CONFIG_PATH = FILEFLOW_HOME / "mcp.json"

DEFAULT_CONFIG = {
    "enabled": False,
    "transport": "stdio",
    "port": 8080,
    "rate_limit": 60,
    "log_audit": True,
    "blocked_tools": [],
}


def load_mcp_config():
    FILEFLOW_HOME.mkdir(parents=True, exist_ok=True)
    if MCP_CONFIG_PATH.exists():
        try:
            with open(MCP_CONFIG_PATH, 'r') as f:
                data = json.load(f)
            merged = {**DEFAULT_CONFIG, **data}
            return merged
        except (json.JSONDecodeError, ValueError):
            pass
    return dict(DEFAULT_CONFIG)


def save_mcp_config(config):
    FILEFLOW_HOME.mkdir(parents=True, exist_ok=True)
    with open(MCP_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def is_mcp_enabled():
    config = load_mcp_config()
    return config.get('enabled', False)
