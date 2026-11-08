"""Cross-interface physical consistency (issue #6, P0).

Every supported entry point should give the same cutoffs for the same physical
problem on the same mesh. The reference is the exact discrete spectrum of the
cell-centred Neumann stencil (see docs/VALIDATION.md), not any interface's own
output, so a regression in the shared solver cannot hide by agreeing with itself.

Documented tolerances (also in docs/VALIDATION.md):
  * in-process paths (GUI helper, JSON runner, MCP):  rtol 1e-10
  * legacy CLI text output, printed to 6 decimals:    1e-6 GHz absolute
  * GUI labels, printed to 3 decimals:                1e-3 GHz absolute (tested in test_gui_session.py)
Intentional differences: the GUI fixes the mesh at 81 x 41 and 4 modes; MCP caps
the mesh at 4096 cells and 4 modes; the bundled JSON example uses 61 x 31.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from openwave.constants import C0
from openwave.gui import GUI_MESH, solve_for_display
from openwave.runner import execute_experiment

ROOT = Path(__file__).resolve().parents[1]
MODES = 4
PROBLEMS = [pytest.param("22.86", "10.16", id="wr90"), pytest.param("30", "12", id="30x12mm")]


def discrete_cutoffs_hz(width_mm, height_mm, nx, ny, count=MODES):
    a, b = width_mm * 1e-3, height_mm * 1e-3
    dx, dy = a / nx, b / ny
    lams = sorted(
        (2 / dx * math.sin(m * math.pi / (2 * nx))) ** 2 + (2 / dy * math.sin(n * math.pi / (2 * ny))) ** 2
        for m in range(nx) for n in range(ny) if (m, n) != (0, 0)
    )[:count]
    return [C0 * math.sqrt(lam) / (2 * math.pi) for lam in lams]


def experiment(width, height):
    nx, ny = GUI_MESH
    return {"schema_version": "1.0", "kind": "rectangular_waveguide_te",
            "geometry": {"width_mm": float(width), "height_mm": float(height)},
            "mesh": {"nx": nx, "ny": ny}, "solver": {"modes": MODES, "seed": 0}}


def run_cli(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), MPLBACKEND="Agg")
    env.pop("DISPLAY", None)
    return subprocess.run([sys.executable, "-m", "openwave", *map(str, args)], cwd=ROOT,
                          env=env, capture_output=True, text=True, timeout=120)


def assert_same_fields_up_to_sign(fields_a, fields_b):
    for a, b in zip(fields_a, fields_b):
        a, b = np.ravel(a), np.ravel(b)
        overlap = abs(a @ b) / (np.linalg.norm(a) * np.linalg.norm(b))
        assert overlap == pytest.approx(1.0, abs=1e-9)


def test_gui_mesh_is_the_historical_solver_default():
    import inspect

    from openwave.waveguide import RectangularWaveguide
    params = inspect.signature(RectangularWaveguide).parameters
    assert GUI_MESH == (params["nx"].default, params["ny"].default)


@pytest.mark.parametrize(("width", "height"), PROBLEMS)
def test_gui_helper_and_json_runner_agree_with_oracle(width, height):
    expected = discrete_cutoffs_hz(float(width), float(height), *GUI_MESH)
    guide, gui_modes = solve_for_display(width, height)
    assert (guide.grid.nx, guide.grid.ny) == GUI_MESH
    result = execute_experiment(experiment(width, height))
    np.testing.assert_allclose([m.cutoff_frequency_hz for m in gui_modes], expected, rtol=1e-10)
    np.testing.assert_allclose([m["cutoff_frequency_hz"] for m in result.modes], expected, rtol=1e-10)
    # First four modes of both problems are non-degenerate, so fields must
    # match individually up to the arbitrary eigenvector sign.
    assert_same_fields_up_to_sign([m.field for m in gui_modes], result.fields)
    np.testing.assert_allclose(guide.grid.x, result.x_m)
    np.testing.assert_allclose(guide.grid.y, result.y_m)


@pytest.mark.parametrize(("width", "height"), PROBLEMS)
def test_legacy_and_json_cli_agree_with_oracle(width, height, tmp_path):
    expected_ghz = np.array(discrete_cutoffs_hz(float(width), float(height), *GUI_MESH)) / 1e9

    legacy = run_cli("--width-mm", width, "--height-mm", height, "--modes", MODES,
                     "--plot", tmp_path / "mode1.png")
    assert legacy.returncode == 0, legacy.stderr
    rows = [line.split(",") for line in legacy.stdout.splitlines() if line[:1].isdigit()]
    assert [int(index) for index, _ in rows] == list(range(1, MODES + 1))
    np.testing.assert_allclose([float(ghz) for _, ghz in rows], expected_ghz, rtol=0, atol=1e-6)

    path = tmp_path / "experiment.json"
    path.write_text(json.dumps(experiment(width, height)))
    run = run_cli("run", path, "--output", tmp_path / "bundle")
    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    np.testing.assert_allclose([m["cutoff_frequency_hz"] / 1e9 for m in report["modes"]],
                               expected_ghz, rtol=1e-10)
    fields = np.load(tmp_path / "bundle" / "fields.npy", allow_pickle=False)
    _, gui_modes = solve_for_display(width, height)
    assert_same_fields_up_to_sign([m.field for m in gui_modes], fields)


def test_json_bundle_sign_convention_holds():
    fields = execute_experiment(experiment("22.86", "10.16")).fields
    for field in fields:
        assert field.flat[np.flatnonzero(np.abs(field.ravel()) > 0.5)[0]] > 0
        assert np.max(np.abs(field)) == pytest.approx(1.0)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize(("width", "height"), PROBLEMS)
async def test_mcp_agrees_with_oracle_and_runner(width, height, tmp_path):
    pytest.importorskip("mcp")
    from mcp import Client

    from openwave.mcp_server import create_server

    expected = discrete_cutoffs_hz(float(width), float(height), *GUI_MESH)
    async with Client(create_server(tmp_path), raise_exceptions=True) as client:
        reply = await client.call_tool("run_experiment",
                                       {"document": experiment(width, height), "run_name": "parity"})
    assert reply.is_error is not True
    modes = reply.structured_content["result"]["modes"]
    np.testing.assert_allclose([m["cutoff_frequency_hz"] for m in modes], expected, rtol=1e-10)
    in_process = execute_experiment(experiment(width, height))
    np.testing.assert_array_equal(np.load(tmp_path / "parity" / "fields.npy"), in_process.fields)
