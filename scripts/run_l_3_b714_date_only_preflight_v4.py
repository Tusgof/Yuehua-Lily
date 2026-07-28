"""v4 is E0 only and deliberately cannot execute or create real artifacts."""
from __future__ import annotations

from lib.environment import interpreter_metadata


def main() -> int:
    interpreter_metadata()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
