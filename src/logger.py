from datetime import datetime

__all__ = ['ColoredLogger']

GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[0m'


class ColoredLogger:

    LEVEL_COLOR = YELLOW
    TEXT_COLOR = GREEN

    def __init__(self, log_file=None):
        self.log_file = log_file

    def _write(self, text):
        print(text)

        if self.log_file:
            clean = text.replace(GREEN, '').replace(YELLOW, '').replace(RESET, '')
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(clean + '\n')

    @staticmethod
    def _get_timestamp():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _format(self, level, message, path=None):
        timestamp = self._get_timestamp()
        level_colored = f"{self.LEVEL_COLOR}[{level}]{RESET}"
        base = f"{self.TEXT_COLOR}[FileFlow]{RESET}"
        if path:
            path_colored = f"{self.TEXT_COLOR}{path}{RESET}"
            return f"{timestamp} {level_colored} {base} {message} {path_colored}"
        else:
            return f"{timestamp} {level_colored} {base} {message}"

    def info(self, message, path=None):
        self._write(self._format("INFO", message, path))

    def debug(self, message, path=None):
        self._write(self._format("DEBUG", message, path))

    def warning(self, message, path=None):
        self._write(self._format("WARNING", message, path))

    def error(self, message, path=None):
        self._write(self._format("ERROR", message, path))
