"""Short-lived, headless runner process used by the bounded MCP adapter."""
from __future__ import annotations

import json
import sys

from .experiment import ExperimentError
from .runner import run_experiment


def main() -> int:
    # This is an internal entry point. The MCP server validates the document and
    # chooses a private staging directory before launching the worker.
    if len(sys.argv) != 2:
        return 2
    try:
        document = json.load(sys.stdin)
        report = run_experiment(document, sys.argv[1])
        print(json.dumps(report, allow_nan=False))
        return 0
    except (ExperimentError, ValueError, OSError, ArithmeticError, RuntimeError) as exc:
        code = "invalid_input" if isinstance(exc, ExperimentError) else "execution_failed"
        print(json.dumps({"error": {"code": code, "message": str(exc)}}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
