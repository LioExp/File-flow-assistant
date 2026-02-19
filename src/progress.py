import sys
import time
from config import GREEN, RESET

class ProgressBar:
    def __init__(self, total, width=50, prefix='Indexing', suffix='',
                 fill_char='█', empty_char='░', color=GREEN, reset=RESET):
        self.total = total
        self.width = width
        self.prefix = prefix
        self.suffix = suffix
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.color = color
        self.reset = reset
        self.current = 0
        self._start_time = time.time()
        self._last_line = ""

    def update(self, n=1):
        self.current += n
        self._draw()

    def _draw(self):
        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        bar = self.fill_char * filled + self.empty_char * (self.width - filled)

        elapsed = time.time() - self._start_time
        elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"

        if self.current > 0:
            rate = self.current / elapsed
            eta = (self.total - self.current) / rate if rate > 0 else 0
            if eta < 60:
                eta_str = f"{eta:.1f}s"
            elif eta < 3600:
                eta_str = f"{eta/60:.1f}m"
            else:
                eta_str = f"{eta/3600:.1f}h"
            rate_str = f"{rate:.1f} files/s"
        else:
            eta_str = "?"
            rate_str = "?"

        # Linha com \r e \033[K para limpar a linha atual
        line = (f"\r\033[K{self.color}{self.prefix} |{bar}| "
                f"{self.current}/{self.total} {percent:.1%} "
                f"[{elapsed_str}<{eta_str}, {rate_str}]{self.reset}")

        sys.stdout.write(line)
        sys.stdout.flush()

        if self.current == self.total:
            sys.stdout.write('\n')
            sys.stdout.flush()