import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from watch_config import FILEFLOW_HOME

__all__ = ['Rule', 'RuleEngine', 'load_rules', 'add_rule', 'remove_rule']

RULES_PATH = FILEFLOW_HOME / "rules.json"

DEFAULT_RULES = [
    {
        "name": "Documents",
        "conditions": {"extension": ".pdf"},
        "action": {"type": "move", "dest": "Docs"}
    },
    {
        "name": "Text Files",
        "conditions": {"extension": ".txt"},
        "action": {"type": "move", "dest": "Docs"}
    },
    {
        "name": "Word Documents",
        "conditions": {"extension": ".docx"},
        "action": {"type": "move", "dest": "Docs"}
    },
    {
        "name": "Images",
        "conditions": {"extension": ".jpg"},
        "action": {"type": "move", "dest": "Imagens"}
    },
    {
        "name": "JPEG Images",
        "conditions": {"extension": ".jpeg"},
        "action": {"type": "move", "dest": "Imagens"}
    },
    {
        "name": "PNG Images",
        "conditions": {"extension": ".png"},
        "action": {"type": "move", "dest": "Imagens"}
    },
    {
        "name": "Videos",
        "conditions": {"extension": ".mp4"},
        "action": {"type": "move", "dest": "Videos"}
    },
    {
        "name": "Compressed",
        "conditions": {"extension": ".zip"},
        "action": {"type": "move", "dest": "Compactados"}
    },
    {
        "name": "RAR Archives",
        "conditions": {"extension": ".rar"},
        "action": {"type": "move", "dest": "Compactados"}
    },
]


class Rule:
    def __init__(self, name: str, conditions: Dict[str, Any], action: Dict[str, Any]):
        self.name = name
        self.conditions = conditions
        self.action = action

    def matches(self, file_path: str, file_stat: os.stat_result) -> bool:
        if 'extension' in self.conditions:
            ext = os.path.splitext(file_path)[1].lower()
            if ext != self.conditions['extension']:
                return False
        if 'keyword' in self.conditions:
            filename = os.path.basename(file_path).lower()
            if self.conditions['keyword'].lower() not in filename:
                return False
        if 'min_size' in self.conditions:
            if file_stat.st_size < self.conditions['min_size']:
                return False
        if 'max_size' in self.conditions:
            if file_stat.st_size > self.conditions['max_size']:
                return False
        if 'older_than_days' in self.conditions:
            age = (time.time() - file_stat.st_mtime) / 86400
            if age < self.conditions['older_than_days']:
                return False
        return True

    def to_dict(self):
        return {
            "name": self.name,
            "conditions": self.conditions,
            "action": self.action,
        }


class RuleEngine:
    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def evaluate(self, file_path: str) -> Optional[Dict]:
        if not os.path.isfile(file_path):
            return None
        stat = os.stat(file_path)
        for rule in self.rules:
            if rule.matches(file_path, stat):
                return rule.action
        return None


def load_rules():
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RULES_PATH.exists():
        with open(RULES_PATH, "r") as f:
            data = json.load(f)
        return [Rule(r["name"], r["conditions"], r["action"]) for r in data]
    return [Rule(r["name"], r["conditions"], r["action"]) for r in DEFAULT_RULES]


def save_rules(rules: List[Rule]):
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RULES_PATH, "w") as f:
        json.dump([r.to_dict() for r in rules], f, indent=2)


def add_rule(name, conditions, action):
    rules = load_rules()
    rules.append(Rule(name, conditions, action))
    save_rules(rules)


def remove_rule(name):
    rules = load_rules()
    rules = [r for r in rules if r.name != name]
    save_rules(rules)
