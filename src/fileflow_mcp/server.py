import os
import json
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from config import WATCH_DIRECTORIES, TRASH_DIR, METADATA_FILE
from database import FileIndex
from fileflow_mcp.security import SecurityPolicy, create_policy

RISKY_TOOLS = {'organize', 'recover', 'clean', 'db_reset'}


def create_fileflow_mcp(security: Optional[SecurityPolicy] = None) -> FastMCP:
    mcp = FastMCP(
        name="FileFlow",
        instructions="File organization assistant. Monitor folders, detect duplicates, organize files safely."
    )
    policy = security or create_policy()

    @mcp.tool()
    def status() -> dict:
        """Get FileFlow system status."""
        err = policy.validate("status", {})
        if err:
            return {"error": err}
        policy.audit_log("status", {}, "ok")

        index = FileIndex()
        file_count = 0
        try:
            import sqlite3
            with sqlite3.connect(index.db_path) as conn:
                file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        except Exception:
            pass

        from rules import load_rules
        return {
            "watch_directories": WATCH_DIRECTORIES,
            "indexed_files": file_count,
            "rules_count": len(load_rules()),
            "trash_dir": str(TRASH_DIR),
        }

    @mcp.tool()
    def list_duplicates() -> dict:
        """List all duplicate files found."""
        err = policy.validate("list_duplicates", {})
        if err:
            return {"error": err}

        from duplicate import DuplicateDetector
        from logger import ColoredLogger

        logger = ColoredLogger()
        detector = DuplicateDetector(logger, WATCH_DIRECTORIES)
        detector._scan_existing_files()
        duplicates = detector.generate_report()

        policy.audit_log("list_duplicates", {}, f"found {len(duplicates)}")
        return {
            "count": len(duplicates),
            "duplicates": duplicates[:50],
        }

    @mcp.tool()
    def list_trash() -> dict:
        """List files in FileFlow trash."""
        err = policy.validate("list_trash", {})
        if err:
            return {"error": err}

        if not METADATA_FILE.exists():
            return {"count": 0, "files": []}

        try:
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {"count": 0, "files": [], "error": "Corrupted metadata"}

        items = []
        for name, info in metadata.items():
            if isinstance(info, dict) and 'original_path' in info:
                items.append({
                    "trash_name": name,
                    "original_path": info.get("original_path", "?"),
                    "deleted_at": info.get("deleted_at", "?"),
                })

        policy.audit_log("list_trash", {}, f"found {len(items)}")
        return {"count": len(items), "files": items}

    @mcp.tool()
    def list_rules() -> dict:
        """List organization rules."""
        err = policy.validate("list_rules", {})
        if err:
            return {"error": err}

        from rules import load_rules
        rules = load_rules()
        items = []
        for r in rules:
            items.append({
                "name": r.name,
                "conditions": r.conditions,
                "action": r.action,
            })

        policy.audit_log("list_rules", {}, f"found {len(items)}")
        return {"count": len(items), "rules": items}

    @mcp.tool()
    def organize_preview() -> dict:
        """Preview files that would be organized (dry run)."""
        err = policy.validate("organize_preview", {})
        if err:
            return {"error": err}

        from organizer import FileOrganizer
        from config import (
            TEMP_BASE_DIR, TEMP_CATEGORIES,
            KEYWORD_PATTERNS, IGNORE_PATTERNS,
            TRIGGER_INACTIVITY_HOURS, WATCH_RECURSIVELY
        )
        from logger import ColoredLogger

        organizer = FileOrganizer(
            logger=ColoredLogger(),
            watch_dirs=WATCH_DIRECTORIES,
            temp_base=TEMP_BASE_DIR,
            categories=TEMP_CATEGORIES,
            patterns=KEYWORD_PATTERNS,
            ignore_patterns=IGNORE_PATTERNS,
            inactivity_hours=TRIGGER_INACTIVITY_HOURS
        )
        files = organizer.preview(recursive=WATCH_RECURSIVELY)

        items = []
        for f in files:
            items.append({
                "source": str(f['source']),
                "category": f['category'],
                "size": f['size'],
                "dest": str(f['dest']),
            })

        policy.audit_log("organize_preview", {}, f"found {len(items)}")
        return {"count": len(items), "files": items}

    @mcp.tool()
    def organize() -> dict:
        """Organize inactive files into categories. WARNING: Moves files."""
        err = policy.validate("organize", {})
        if err:
            return {"error": err}

        from organizer import FileOrganizer
        from config import (
            TEMP_BASE_DIR, TEMP_CATEGORIES,
            KEYWORD_PATTERNS, IGNORE_PATTERNS,
            TRIGGER_INACTIVITY_HOURS, WATCH_RECURSIVELY
        )
        from logger import ColoredLogger

        organizer = FileOrganizer(
            logger=ColoredLogger(),
            watch_dirs=WATCH_DIRECTORIES,
            temp_base=TEMP_BASE_DIR,
            categories=TEMP_CATEGORIES,
            patterns=KEYWORD_PATTERNS,
            ignore_patterns=IGNORE_PATTERNS,
            inactivity_hours=TRIGGER_INACTIVITY_HOURS
        )
        files = organizer.preview(recursive=WATCH_RECURSIVELY)
        moved = 0
        for f in files:
            if organizer.organize_file(f['source']):
                moved += 1

        policy.audit_log("organize", {}, f"moved {moved} files")
        return {"moved": moved, "total": len(files)}

    @mcp.tool()
    def recover(identifier: str) -> dict:
        """Recover a file from trash by name or index."""
        err = policy.validate("recover", {"file": identifier})
        if err:
            return {"error": err}

        from services import trash_recover
        dest, error = trash_recover(identifier)

        if error:
            policy.audit_log("recover", {"identifier": identifier}, error, error=True)
            return {"error": error}

        policy.audit_log("recover", {"identifier": identifier}, f"recovered to {dest}")
        return {"recovered": str(dest)}

    @mcp.tool()
    def clean() -> dict:
        """Remove expired files from trash (older than 30 days)."""
        err = policy.validate("clean", {})
        if err:
            return {"error": err}

        from trash import clean_expired
        count = clean_expired()

        policy.audit_log("clean", {}, f"removed {count}")
        return {"removed": count}

    @mcp.tool()
    def scan_file(file: str) -> dict:
        """Scan a single file for malware."""
        err = policy.validate("scan_file", {"path": file})
        if err:
            return {"error": err}

        from scanner import VirusScanner
        scanner = VirusScanner()

        if not scanner.is_available():
            return {"error": "No antivirus found. Install ClamAV or Windows Defender."}

        result = scanner.scan_file(file)
        policy.audit_log("scan_file", {"file": file}, result.get("status", "unknown"))
        return result

    @mcp.tool()
    def scan_directory(dir: str = ".") -> dict:
        """Scan a directory for malware."""
        err = policy.validate("scan_directory", {"path": dir})
        if err:
            return {"error": err}

        from scanner import VirusScanner
        scanner = VirusScanner()

        if not scanner.is_available():
            return {"error": "No antivirus found. Install ClamAV or Windows Defender."}

        results = scanner.scan_directory(dir)
        clean = sum(1 for r in results if r['status'] == 'clean')
        infected = [r for r in results if r['status'] == 'infected']

        policy.audit_log("scan_directory", {"dir": dir}, f"clean={clean} infected={len(infected)}")
        return {
            "clean": clean,
            "infected": len(infected),
            "infected_files": infected[:20],
        }

    @mcp.tool()
    def classify_file(file: str) -> dict:
        """Suggest the best category for a file based on its content/name."""
        err = policy.validate("classify_file", {"path": file})
        if err:
            return {"error": err}

        p = Path(file)
        if not p.exists():
            return {"error": f"File not found: {file}"}

        ext = p.suffix.lower()
        name = p.stem.lower()

        from config import TEMP_CATEGORIES, KEYWORD_PATTERNS

        category = TEMP_CATEGORIES.get(ext, TEMP_CATEGORIES.get('default', 'Outros'))
        for keyword, cat in KEYWORD_PATTERNS.items():
            if keyword in name:
                category = cat
                break

        policy.audit_log("classify_file", {"file": file}, category)
        return {
            "file": file,
            "extension": ext,
            "suggested_category": category,
            "size": p.stat().st_size,
        }

    @mcp.tool()
    def add_rule(
        name: str,
        extension: Optional[str] = None,
        keyword: Optional[str] = None,
        dest: str = "Outros"
    ) -> dict:
        """Add a new organization rule."""
        err = policy.validate("add_rule", {"name": name})
        if err:
            return {"error": err}

        conditions = {}
        if extension:
            conditions['extension'] = extension.lower()
        if keyword:
            conditions['keyword'] = keyword

        if not conditions:
            return {"error": "Provide at least extension or keyword"}

        from rules import add_rule as do_add_rule
        action = {"type": "move", "dest": dest}
        do_add_rule(name, conditions, action)

        policy.audit_log("add_rule", {"name": name, "conditions": conditions}, "ok")
        return {"added": name, "conditions": conditions, "dest": dest}

    @mcp.tool()
    def remove_rule(name: str) -> dict:
        """Remove an organization rule by name."""
        err = policy.validate("remove_rule", {"name": name})
        if err:
            return {"error": err}

        from rules import remove_rule as do_remove_rule
        do_remove_rule(name)

        policy.audit_log("remove_rule", {"name": name}, "ok")
        return {"removed": name}

    return mcp
