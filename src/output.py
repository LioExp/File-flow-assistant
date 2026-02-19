'''
from abc import ABC, abstractmethod

class Output(ABC):
    """Interface para exibir notificações de eventos de arquivo."""
    @abstractmethod
    def on_event(self, event_type: str, src_path: str, dest_path: str = None) -> None:
        """
        :param event_type: 'created', 'modified', 'deleted' ou 'moved'
        :param src_path: caminho de origem
        :param dest_path: caminho de destino (apenas para 'moved')
        """
        pass


class TerminalColorOutput(Output):
    """Exibe eventos no terminal com cores fixas por tipo de evento."""
    CORES = {
        'created': '\033[32m',   # verde
        'modified': '\033[33m',  # amarelo
        'deleted': '\033[31m',   # vermelho
        'moved': '\033[34m',     # azul
    }
    RESET = '\033[0m'

    def on_event(self, event_type, src_path, dest_path=None):
        cor = self.CORES.get(event_type, '')
        if event_type == 'moved' and dest_path:
            print(f"FFA detectou arquivo movido: {cor}{src_path} -> {dest_path}{self.RESET}")
        else:
            print(f"FFA detectou arquivo {event_type}: {cor}{src_path}{self.RESET}")
        print('===' * 12)
'''