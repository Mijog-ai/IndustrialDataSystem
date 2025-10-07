"""Entrypoint launching the GUI application."""
from __future__ import annotations

from src.gui.login_window import LoginWindow
from src.utils.logger import configure_logging


def main() -> None:
    configure_logging()
    app = LoginWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
