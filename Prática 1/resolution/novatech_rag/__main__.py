"""Entrypoint do módulo: `python -m novatech_rag ingest|query|eval`."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
