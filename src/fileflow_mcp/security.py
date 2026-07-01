import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Set, Optional

from config import TRASH_DIR, METADATA_FILE, FILEFLOW_HOME

logger = logging.getLogger(__name__)

AUDIT_LOG = FILEFLOW_HOME / "mcp_audit.jsonl"


class SecurityPolicy:
    def __init__(self, allowed_dirs=None, rate_limit=60, log_file=None):
        self.allowed_dirs = set(allowed_dirs or [])
        self.rate_limit = rate_limit
        self.log_file = log_file or AUDIT_LOG
        self._call_counts = defaultdict(list)
        self._blocked_tools: Set[str] = set()

    def is_path_allowed(self, path: str) -> bool:
        resolved = str(Path(path).expanduser().resolve())
        return any(
            resolved.startswith(str(Path(d).expanduser().resolve()))
            for d in self.allowed_dirs
        )

    def check_rate_limit(self, tool_name: str) -> bool:
        now = time.time()
        window = 60
        self._call_counts[tool_name] = [
            t for t in self._call_counts[tool_name] if now - t < window
        ]
        if len(self._call_counts[tool_name]) >= self.rate_limit:
            return False
        self._call_counts[tool_name].append(now)
        return True

    def is_tool_blocked(self, tool_name: str) -> bool:
        return tool_name in self._blocked_tools

    def block_tool(self, tool_name: str):
        self._blocked_tools.add(tool_name)

    def unblock_tool(self, tool_name: str):
        self._blocked_tools.discard(tool_name)

    def audit_log(self, tool_name: str, args: dict, result: str, error: bool = False):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'tool': tool_name,
            'args': args,
            'result': result[:500],
            'error': error,
        }
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.warning(f"Failed to write audit log: {e}")

    def validate(self, tool_name: str, args: dict) -> Optional[str]:
        if self.is_tool_blocked(tool_name):
            return f"Tool '{tool_name}' is blocked"

        if not self.check_rate_limit(tool_name):
            return f"Rate limit exceeded for '{tool_name}' (max {self.rate_limit}/min)"

        path_args = ['path', 'file', 'dir', 'directory', 'source', 'dest']
        for key in path_args:
            if key in args and isinstance(args[key], str):
                if not self.is_path_allowed(args[key]):
                    return f"Access denied: path '{args[key]}' is outside allowed directories"

        return None


def create_policy(allowed_dirs=None, rate_limit=60) -> SecurityPolicy:
    from config import WATCH_DIRECTORIES
    dirs = allowed_dirs or WATCH_DIRECTORIES
    return SecurityPolicy(allowed_dirs=dirs, rate_limit=rate_limit)
