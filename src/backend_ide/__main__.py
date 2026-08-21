"""Entry point for python -m backend_ide invocation."""

from __future__ import annotations

import sys

from backend_ide.main import main

if __name__ == "__main__":
    sys.exit(main())
