"""Local stdio MCP tools for bounded, declarative OpenWave experiments.

The MCP dependency is optional so the Python 3.10 CLI and GUI remain usable.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .experiment import ExperimentError, experiment_schema
from .experiment import validate_experiment as validate_document

try:
    from mcp.server import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError as exc:
    raise ImportError(
        "OpenWave MCP requires Python 3.11+ and the optional extra: "
        "python -m pip install -e '.[mcp]'"
    ) from exc


MAX_CELLS = 4096
MAX_MODES = 4
TIMEOUT_SECONDS = 45
RUN_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def _checked_document(document: object) -> dict:
    try:
        normalized = validate_document(document)
    except ExperimentError as exc:
        raise ToolError(f"invalid_input: {exc}") from exc
    cells = normalized["mesh"]["nx"] * normalized["mesh"]["ny"]
    if cells > MAX_CELLS:
        raise ToolError(f"resource_limit: mesh has {cells} cells; MCP maximum is {MAX_CELLS}")
    if normalized["solver"]["modes"] > MAX_MODES:
        raise ToolError(f"resource_limit: MCP allows at most {MAX_MODES} modes")
    return normalized


def _output_root(path: Path) -> Path:
    # The operator chooses the root, never the tool caller. Refuse a symlink at
    # that boundary and create it only when an actual run is requested.
    if path.is_symlink():
        raise ToolError("invalid_output: configured output root must not be a symlink")
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir() or path.is_symlink():
            raise ToolError("invalid_output: output root is not a regular directory")
        return path.resolve(strict=True)
    except OSError as exc:
        raise ToolError(f"io_error: cannot prepare configured output root: {exc}") from exc


def _run_bounded(document: dict, name: str, output_root: Path) -> dict:
    if not isinstance(name, str) or not RUN_NAME.fullmatch(name):
        raise ToolError("invalid_output: run_name must be 1-64 ASCII letters, digits, _ or -, starting with a letter or digit")
    normalized = _checked_document(document)
    root = _output_root(output_root)
    destination = root / name
    if destination.exists() or destination.is_symlink():
        raise ToolError(f"output_exists: run {name!r} already exists; choose a new run_name")

    # Parent owns the temporary directory so a killed or failed worker cannot
    # publish a partial bundle. run_experiment still does its own atomic staging.
    with tempfile.TemporaryDirectory(prefix=".openwave-mcp-", dir=root) as temporary:
        work_output = Path(temporary) / "bundle"
        env = dict(os.environ, MPLBACKEND="Agg", OPENBLAS_NUM_THREADS="1",
                   OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "openwave.mcp_worker", str(work_output)],
                input=json.dumps(normalized, allow_nan=False), capture_output=True,
                text=True, encoding="utf-8", timeout=TIMEOUT_SECONDS, env=env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"resource_limit: solve exceeded {TIMEOUT_SECONDS}s timeout") from exc
        except OSError as exc:
            raise ToolError(f"execution_failed: could not start solver: {exc}") from exc
        if completed.returncode:
            try:
                error = json.loads(completed.stderr)["error"]
                raise ToolError(f"{error['code']}: {error['message']}")
            except (ValueError, KeyError, TypeError) as exc:
                raise ToolError("execution_failed: solver worker failed; no output was published") from exc
        try:
            report = json.loads(completed.stdout)
            if report["status"] != "success" or not (work_output / "results.json").is_file():
                raise ValueError("missing output bundle")
        except (ValueError, KeyError, TypeError) as exc:
            raise ToolError("execution_failed: solver returned an invalid report") from exc
        if destination.exists() or destination.is_symlink():
            raise ToolError(f"output_exists: run {name!r} already exists; choose a new run_name")
        try:
            work_output.rename(destination)
        except OSError as exc:
            raise ToolError(f"io_error: cannot publish output bundle: {exc}") from exc
        return {"status": "success", "run_name": name, "output_dir": str(destination), "result": report}


def create_server(output_root: str | Path | None = None) -> MCPServer:
    """Build a server with one operator-controlled root, suitable for client tests."""
    root = Path(output_root) if output_root is not None else Path.cwd() / "artifacts" / "mcp"
    server = MCPServer("OpenWave")

    @server.tool()
    def get_experiment_schema() -> dict[str, Any]:
        """Return the full JSON Schema for an OpenWave experiment (version 1.0)."""
        return experiment_schema()

    @server.tool()
    def validate_experiment(document: dict[str, Any]) -> dict[str, Any]:
        """Validate a JSON experiment, including MCP mesh/mode limits; do not solve."""
        normalized = _checked_document(document)
        return {"status": "valid", "schema_version": normalized["schema_version"],
                "experiment": normalized,
                "limits": {"max_cells": MAX_CELLS, "max_modes": MAX_MODES,
                           "timeout_seconds": TIMEOUT_SECONDS}}

    @server.tool()
    def run_experiment(document: dict[str, Any], run_name: str) -> dict[str, Any]:
        """Solve into a new directory beneath the configured root; never overwrite."""
        return _run_bounded(document, run_name, root)

    return server


mcp = create_server()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Local stdio MCP server for OpenWave")
    parser.add_argument("--output-root", type=Path,
                        default=Path.cwd() / "artifacts" / "mcp",
                        help="Operator-controlled directory for MCP result bundles")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error("MCP requires Python 3.11 or later")
    create_server(args.output_root).run(transport="stdio")


if __name__ == "__main__":
    main()
