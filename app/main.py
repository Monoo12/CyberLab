"""Entrypoint de la app del visitante.

Uso:
    python -m app.main                      (usa config.toml)
    python -m app.main --engine simulated   (override del motor)
    python -m app.main --level advanced --no-visual
    python -m app.main --autostart          (salta el menu; modo kiosco)
"""
from __future__ import annotations

import sys

from app.config import load_config
from app.ui.app import MissionApp


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    cfg = load_config(argv=argv)
    app = MissionApp(cfg)
    app.run()


if __name__ == "__main__":
    main()
