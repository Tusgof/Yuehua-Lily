from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = PROJECT_ROOT / "tests"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _root_test_suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for path in sorted(TESTS_ROOT.glob("test_*.py")):
        module = ".".join(path.relative_to(PROJECT_ROOT).with_suffix("").parts)
        suite.addTests(loader.loadTestsFromName(module))
    hermetic_dir = TESTS_ROOT / "hermetic"
    if hermetic_dir.exists():
        suite.addTests(
            loader.discover(
                start_dir=str(hermetic_dir),
                pattern="test_*.py",
                top_level_dir=str(PROJECT_ROOT),
            )
        )
    return suite


def _state_audit_suite() -> unittest.TestSuite | None:
    state_dir = TESTS_ROOT / "state_audit"
    if not state_dir.exists():
        return None
    return unittest.TestLoader().discover(
        start_dir=str(state_dir),
        pattern="test_*.py",
        top_level_dir=str(PROJECT_ROOT),
    )


def _run_suite(name: str, suite: unittest.TestSuite, verbosity: int) -> bool:
    print(f"RUN {name}")
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return result.wasSuccessful()


def run_tier(tier: str, *, verbosity: int = 1) -> bool:
    if tier == "hermetic":
        return _run_suite("hermetic", _root_test_suite(), verbosity)
    if tier == "state-audit":
        suite = _state_audit_suite()
        if suite is None:
            print("SKIP state-audit: tests/state_audit is not present")
            return True
        return _run_suite("state-audit", suite, verbosity)
    if tier == "all":
        if not run_tier("hermetic", verbosity=verbosity):
            return False
        return run_tier("state-audit", verbosity=verbosity)
    raise ValueError(f"Unsupported tier: {tier}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Lily's explicit test tiers.")
    parser.add_argument("tier", choices=("hermetic", "state-audit", "all"))
    parser.add_argument("--verbosity", type=int, choices=(0, 1, 2), default=1)
    args = parser.parse_args()
    return 0 if run_tier(args.tier, verbosity=args.verbosity) else 1


if __name__ == "__main__":
    raise SystemExit(main())
