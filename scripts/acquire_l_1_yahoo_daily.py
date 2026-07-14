from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.environment import require_configured_path
from lib.yahoo_daily import acquire_symbols


SYMBOLS = [
    ("VTI", date(2001, 5, 24)),
    ("VGK", date(2005, 3, 4)),
    ("EWJ", date(1996, 3, 12)),
    ("VWO", date(2005, 3, 4)),
    ("IEF", date(2002, 7, 22)),
    ("TIP", date(2003, 12, 4)),
    ("GLD", date(2004, 11, 18)),
    ("DBC", date(2006, 2, 3)),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire the locked L-1 falsification dataset only.")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    data_root = args.data_root.resolve() if args.data_root else require_configured_path("LILY_DATA_ROOT")
    result = acquire_symbols(
        SYMBOLS,
        start=date(2006, 2, 3),
        cutoff_inclusive=date(2015, 12, 31),
        data_root=data_root,
        acquired_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
