"""Allows `python -m mt564_bridge convert ...` as an alternative to the console script."""

import sys

from .cli import main

sys.exit(main())
