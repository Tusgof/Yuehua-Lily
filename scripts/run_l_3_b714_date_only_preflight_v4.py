"""v4 is E0 only and deliberately cannot execute a real preflight."""
from __future__ import annotations
import sys
from lib.environment import interpreter_metadata
def main()->int:return 2
if __name__=='__main__':raise SystemExit(main())
