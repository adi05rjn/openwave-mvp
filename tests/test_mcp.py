"""Real MCP-client contract, stdio transport and sandbox regressions."""
from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

pytest.importorskip("mcp")
from mcp import Client, StdioServerParameters

from openwave.experiment import experiment_schema
from openwave.mcp_server import create_server

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/wr90.json").read_text())


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_tools_schema_validation_and_clear_input_errors(tmp_path):
    async with Client(create_server(tmp_path), raise_exceptions=True) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools.tools} == {
            "get_experiment_schema", "validate_experiment", "run_experiment"
        }
        schema = await client.call_tool("get_experiment_schema", {})
        assert schema.is_error is not True
        assert schema.structured_content == experiment_schema()
        document = deepcopy(EXAMPLE)
        valid = await client.call_tool("validate_experiment", {"document": document})
        assert valid.structured_content["status"] == "valid"
        assert valid.structured_content["limits"]["max_cells"] == 4096
        document["geometry"]["width_mm"] = -1
        bad = await client.call_tool("validate_experiment", {"document": document})
        assert bad.is_error is True
        assert "invalid_input" in bad.content[0].text
        assert "width_mm" in bad.content[0].text
        assert not list(tmp_path.iterdir())


@pytest.mark.anyio
async def test_bounded_run_artifacts_no_overwrite_and_path_rejections(tmp_path):
    async with Client(create_server(tmp_path), raise_exceptions=True) as client:
        invalid_names = ["../escape", "path/name", ".hidden", "", "a" * 65, "a\\b"]
        for name in invalid_names:
            rejected = await client.call_tool("run_experiment", {"document": EXAMPLE, "run_name": name})
            assert rejected.is_error is True
            assert "invalid_output" in rejected.content[0].text
        success = await client.call_tool("run_experiment", {"document": EXAMPLE, "run_name": "mcp-wr90"})
        assert success.is_error is not True
        report = success.structured_content
        assert report["status"] == "success"
        assert report["result"]["field"]["shape"] == [4, 31, 61]
        assert (tmp_path / "mcp-wr90" / "results.json").is_file()
        assert Path(report["output_dir"]).resolve() == (tmp_path / "mcp-wr90").resolve()
        repeat = await client.call_tool("run_experiment", {"document": EXAMPLE, "run_name": "mcp-wr90"})
        assert repeat.is_error is True
        assert "output_exists" in repeat.content[0].text
        assert not list(tmp_path.glob(".openwave-mcp-*"))


@pytest.mark.anyio
async def test_resource_limits_are_enforced_before_worker(tmp_path):
    async with Client(create_server(tmp_path), raise_exceptions=True) as client:
        for mesh, modes in [({"nx": 65, "ny": 65}, 4), ({"nx": 24, "ny": 12}, 5)]:
            document = deepcopy(EXAMPLE)
            document["mesh"] = mesh
            document["solver"]["modes"] = modes
            for tool, kwargs in [("validate_experiment", {}), ("run_experiment", {"run_name": "blocked"})]:
                result = await client.call_tool(tool, {"document": document, **kwargs})
                assert result.is_error is True
                assert "resource_limit" in result.content[0].text
        assert not list(tmp_path.iterdir())


@pytest.mark.anyio
async def test_symlinked_output_root_refused(tmp_path):
    actual = tmp_path / "real"
    actual.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    async with Client(create_server(alias), raise_exceptions=True) as client:
        result = await client.call_tool("run_experiment", {"document": EXAMPLE, "run_name": "nope"})
        assert result.is_error is True
        assert "invalid_output" in result.content[0].text
    assert not list(actual.iterdir())


@pytest.mark.anyio
async def test_worker_timeout_leaves_no_partial_bundle(tmp_path):
    from subprocess import TimeoutExpired
    async with Client(create_server(tmp_path), raise_exceptions=True) as client:
        with patch("openwave.mcp_server.subprocess.run", side_effect=TimeoutExpired("worker", 45)):
            result = await client.call_tool("run_experiment", {"document": EXAMPLE, "run_name": "timeout"})
        assert result.is_error is True
        assert "timeout" in result.content[0].text
    assert not list(tmp_path.iterdir())


@pytest.mark.anyio
async def test_worker_failure_propagates_safe_error_and_cleans_up(tmp_path):
    failed = CompletedProcess(
        args=["worker"], returncode=1, stdout="",
        stderr=json.dumps({"error": {"code": "execution_failed", "message": "solver did not converge"}}),
    )
    async with Client(create_server(tmp_path), raise_exceptions=True) as client:
        with patch("openwave.mcp_server.subprocess.run", return_value=failed):
            result = await client.call_tool("run_experiment", {"document": EXAMPLE, "run_name": "failed"})
        assert result.is_error is True
        assert "solver did not converge" in result.content[0].text
    assert not list(tmp_path.iterdir())


@pytest.mark.anyio
async def test_real_stdio_transport_and_worker(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), MPLBACKEND="Agg")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "openwave.mcp_server", "--output-root", str(tmp_path)],
        env=env,
    )
    async with Client(params) as client:
        tools = await client.list_tools()
        assert "run_experiment" in {tool.name for tool in tools.tools}
        valid = await client.call_tool("validate_experiment", {"document": EXAMPLE})
        assert valid.structured_content["status"] == "valid"
        run = await client.call_tool("run_experiment", {"document": EXAMPLE, "run_name": "stdio"})
        assert run.structured_content["result"]["status"] == "success"
    assert (tmp_path / "stdio" / "experiment.json").exists()
