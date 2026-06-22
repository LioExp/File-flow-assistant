import os
import re
from typing import List, Dict, Any, Optional

class Rule:
    def __init__(self, name: str, conditions: Dict[str, Any], action: Dict[str, Any]):
        self.name = name
        self.conditions = conditions   # ex: {'extension': '.pdf', 'min_size': 0}
        self.action = action           # ex: {'type': 'move', 'dest': 'Docs'}

    def matches(self, file_path: str, file_stat: os.stat_result) -> bool:
        """Verifica se o arquivo atende às condições da regra."""
        # Extensão
        if 'extension' in self.conditions:
            ext = os.path.splitext(file_path)[1].lower()
            if ext != self.conditions['extension']:
                return False
        # Palavra-chave no nome
        if 'keyword' in self.conditions:
            filename = os.path.basename(file_path).lower()
            if self.conditions['keyword'].lower() not in filename:
                return False
        # Tamanho mínimo
        if 'min_size' in self.conditions:
            if file_stat.st_size < self.conditions['min_size']:
                return False
        # Tamanho máximo
        if 'max_size' in self.conditions:
            if file_stat.st_size > self.conditions['max_size']:
                return False
        # Dias desde última modificação
        if 'older_than_days' in self.conditions:
            import time
            age = (time.time() - file_stat.st_mtime) / 86400
            if age < self.conditions['older_than_days']:
                return False
        # ... outras condições (padrões regex, etc.)
        return True

class RuleEngine:
    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def evaluate(self, file_path: str) -> Optional[Dict]:
        """Retorna a primeira ação aplicável ao arquivo."""
        if not os.path.isfile(file_path):
            return None
        stat = os.stat(file_path)
        for rule in self.rules:
            if rule.matches(file_path, stat):
                return rule.action
        return None