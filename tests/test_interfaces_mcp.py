"""MCP leg of the cross-interface consistency check (see test_interfaces.py).

A separate file so the whole module is skipped when the optional ``mcp`` package
is absent (Python 3.10, or no ``[mcp]`` extra): async tests need its anyio plugin.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mcp")
from mcp import Client  # noqa: E402
from test_interfaces import PROBLEMS, discrete_cutoffs_hz, experiment  # noqa: E402

from openwave.gui import GUI_MESH  # noqa: E402
from openwave.mcp_server import create_server  # noqa: E402
from openwave.runner import execute_experiment  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize(("width", "height"), PROBLEMS)
async def test_mcp_agrees_with_oracle_and_runner(width, height, tmp_path):
    expected = discrete_cutoffs_hz(float(width), float(height), *GUI_MESH)
    async with Client(create_server(tmp_path), raise_exceptions=True) as client:
        reply = await client.call_tool(
            "run_experiment", {"document": experiment(width, height), "run_name": "parity"}
        )
    assert reply.is_error is not True
    modes = reply.structured_content["result"]["modes"]
    np.testing.assert_allclose([m["cutoff_frequency_hz"] for m in modes], expected, rtol=1e-10)
    in_process = execute_experiment(experiment(width, height))
    # Same sign convention and seed, but a separate process with single-threaded
    # BLAS, so floating-point summation order can differ: compare to tolerance.
    np.testing.assert_allclose(
        np.load(tmp_path / "parity" / "fields.npy"), in_process.fields, rtol=0, atol=1e-8)
