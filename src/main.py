import sys
from cli import app, _show_dashboard

if __name__ == "__main__":
    if len(sys.argv) == 1:
        _show_dashboard()
    else:
        app()
