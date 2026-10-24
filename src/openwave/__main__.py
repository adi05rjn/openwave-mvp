"""Allow python -m openwave in source checkouts and installed packages."""
from .cli import main

raise SystemExit(main())
