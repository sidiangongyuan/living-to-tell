"""Application entry point."""
from __future__ import annotations

from writer.app.bootstrap import run


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
