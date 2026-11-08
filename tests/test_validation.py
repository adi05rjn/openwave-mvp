"""Numerical validation against independent closed-form oracles.

Two oracles are used, both derived in docs/VALIDATION.md and neither computed
by OpenWave's solver:

* the continuum TE(m,n) cutoff of an ideal PEC rectangular guide, and
* the exact eigenpairs of the cell-centred Neumann five-point stencil, whose
  eigenvectors are cos(m pi x/a) cos(n pi y/b) sampled at cell centres and whose
  eigenvalues are (2/dx sin(m pi/2nx))^2 + (2/dy sin(n pi/2ny))^2.

The second oracle separates eigensolver error (should be near round-off) from
discretization error (second order, with a known leading term).
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
from openwave.operators import negative_neumann_laplacian_2d
from openwave.waveguide import RectangularWaveguide

ROOT = Path(__file__).resolve().parents[1]
MM = 1e-3


def continuum_hz(a, b, m, n):
    return C0 / 2.0 * math.hypot(m / a, n / b)


def discrete_spectrum(a, b, nx, ny, count):
    dx, dy = a / nx, b / ny
    pairs = sorted(
        ((2 / dx * math.sin(m * math.pi / (2 * nx))) ** 2
         + (2 / dy * math.sin(n * math.pi / (2 * ny))) ** 2, m, n)
        for m in range(nx) for n in range(ny) if (m, n) != (0, 0)
    )
    return pairs[:count]


def lam_to_hz(lam):
    return C0 * math.sqrt(lam) / (2 * math.pi)


def sampled_mode(a, b, nx, ny, m, n):
    x = (np.arange(nx) + 0.5) * a / nx
    y = (np.arange(ny) + 0.5) * b / ny
    field = np.outer(np.cos(n * np.pi * y / b), np.cos(m * np.pi * x / a)).ravel()
    return field / np.linalg.norm(field)


def subspace_sine(basis_a, basis_b):
    qa, _ = np.linalg.qr(basis_a)
    qb, _ = np.linalg.qr(basis_b)
    return float(np.linalg.norm(qa - qb @ (qb.T @ qa), 2))


def unit_fields(modes):
    return np.stack([m.field.ravel() / np.linalg.norm(m.field) for m in modes], axis=1)


GEOMETRIES = [
    pytest.param(22.86, 10.16, 90, 40, id="wr90"),
    pytest.param(10.16, 22.86, 40, 90, id="wr90-rotated"),
    pytest.param(7.112, 3.556, 80, 40, id="wr28-degenerate"),
    pytest.param(10.0, 10.0, 48, 48, id="square-degenerate"),
    pytest.param(20.0, 10.05, 80, 40, id="near-degenerate"),
    pytest.param(30.0, 5.0, 60, 12, id="aspect-6"),
]


@pytest.mark.parametrize(("width", "height", "nx", "ny"), GEOMETRIES)
def test_eigenvalues_match_exact_discrete_spectrum(width, height, nx, ny):
    a, b = width * MM, height * MM
    modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(8, seed=0)
    expected = [lam_to_hz(lam) for lam, _, _ in discrete_spectrum(a, b, nx, ny, 8)]
    np.testing.assert_allclose([m.cutoff_frequency_hz for m in modes], expected, rtol=1e-10)


@pytest.mark.parametrize(("width", "height", "nx", "ny"), GEOMETRIES)
def test_discretization_error_matches_leading_order_prediction(width, height, nx, ny):
    """Explains the observed error: -(kx^4 dx^2 + ky^4 dy^2) / (24 kc^2)."""
    a, b = width * MM, height * MM
    modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(8, seed=0)
    for mode, (_, m, n) in zip(modes, discrete_spectrum(a, b, nx, ny, 8)):
        kx, ky = m * math.pi / a, n * math.pi / b
        predicted = -(kx**4 * (a / nx) ** 2 + ky**4 * (b / ny) ** 2) / (24 * (kx**2 + ky**2))
        observed = mode.cutoff_frequency_hz / continuum_hz(a, b, m, n) - 1
        assert observed < 0, "this stencil underestimates every cutoff"
        assert observed == pytest.approx(predicted, rel=0.02)


@pytest.mark.parametrize(("width", "height", "nx", "ny"), GEOMETRIES)
def test_fields_orthonormal_residual_and_shape(width, height, nx, ny):
    a, b = width * MM, height * MM
    count = 8
    modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(count, seed=0)
    fields = unit_fields(modes)
    np.testing.assert_allclose(fields.T @ fields, np.eye(count), atol=1e-10)

    operator = negative_neumann_laplacian_2d(nx, ny, a / nx, b / ny)
    for mode, vector in zip(modes, fields.T):
        lam = mode.cutoff_wavenumber**2
        assert np.linalg.norm(operator @ vector - lam * vector) / lam < 1e-9

    # Compare each solver mode with the oracle eigenspace of its eigenvalue,
    # looking past the requested count so a split degenerate group is whole.
    extended = discrete_spectrum(a, b, nx, ny, count + 6)
    for i, mode in enumerate(modes):
        lam = mode.cutoff_wavenumber**2
        space = [sampled_mode(a, b, nx, ny, m, n) for value, m, n in extended
                 if abs(value - lam) <= 1e-9 * lam]
        assert space, f"mode {i + 1} has no oracle eigenvalue"
        assert subspace_sine(fields[:, [i]], np.stack(space, axis=1)) < 1e-8


def test_non_degenerate_field_is_sampled_analytic_mode():
    a, b, nx, ny = 22.86 * MM, 10.16 * MM, 90, 40
    modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(4, seed=0)
    for mode, (_, m, n) in zip(modes, discrete_spectrum(a, b, nx, ny, 4)):
        overlap = abs(sampled_mode(a, b, nx, ny, m, n) @ mode.field.ravel()) / np.linalg.norm(mode.field)
        assert overlap == pytest.approx(1.0, abs=1e-12)


def test_rotated_guide_has_identical_spectrum():
    wide = RectangularWaveguide(22.86 * MM, 10.16 * MM, 90, 40).solve_te_modes(8, seed=0)
    tall = RectangularWaveguide(10.16 * MM, 22.86 * MM, 40, 90).solve_te_modes(8, seed=0)
    np.testing.assert_allclose([m.cutoff_frequency_hz for m in wide],
                               [m.cutoff_frequency_hz for m in tall], rtol=1e-10)


@pytest.mark.parametrize(("m", "n"), [(1, 0), (2, 0), (0, 1), (1, 1), (3, 0)])
def test_higher_modes_converge_at_second_order(m, n):
    a, b = 22.86 * MM, 10.16 * MM
    errors = []
    for nx, ny in [(18, 8), (36, 16), (72, 32)]:
        modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(6, seed=0)
        labels = [(p, q) for _, p, q in discrete_spectrum(a, b, nx, ny, 6)]
        numerical = modes[labels.index((m, n))].cutoff_frequency_hz
        errors.append(abs(numerical / continuum_hz(a, b, m, n) - 1))
    orders = [math.log2(coarse / fine) for coarse, fine in zip(errors, errors[1:])]
    assert all(1.95 < order < 2.05 for order in orders), orders


def test_degenerate_pair_subspace_is_seed_independent():
    a = b = 10 * MM
    runs = [RectangularWaveguide(a, b, 48, 48).solve_te_modes(2, seed=s) for s in range(5)]
    bases = [unit_fields(modes) for modes in runs]
    for basis in bases[1:]:
        assert subspace_sine(basis, bases[0]) < 1e-10


def test_rotating_a_degenerate_pair_gives_equally_valid_modes():
    """Why individual degenerate fields carry no meaning, shown deterministically.

    Rotating the two solver vectors by 45 degrees inside their shared eigenspace
    gives vectors that are just as good eigenpairs (same eigenvalue, residual at
    round-off) yet overlap the originals by only cos(45 deg). Whether a given
    ARPACK run happens to return such a rotation depends on library versions, so
    that is documented in VALIDATION.md rather than asserted here.
    """
    a = b = 10 * MM
    nx = ny = 48
    modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(2, seed=0)
    assert modes[0].cutoff_wavenumber == pytest.approx(modes[1].cutoff_wavenumber, rel=1e-10)
    pair = unit_fields(modes)
    c = s = math.sqrt(0.5)
    rotated = pair @ np.array([[c, -s], [s, c]])
    operator = negative_neumann_laplacian_2d(nx, ny, a / nx, b / ny)
    lam = modes[0].cutoff_wavenumber**2
    for vector in rotated.T:
        assert np.linalg.norm(operator @ vector - lam * vector) / lam < 1e-9
    assert abs(rotated[:, 0] @ pair[:, 0]) == pytest.approx(math.sqrt(0.5), abs=1e-12)


def test_coarse_anisotropic_mesh_can_reorder_near_degenerate_modes():
    """Documented pitfall: solver index is not an analytical label."""
    a, b = 20.0 * MM, 10.05 * MM
    assert continuum_hz(a, b, 0, 1) < continuum_hz(a, b, 2, 0)
    for (nx, ny), expected_second in [((10, 20), (2, 0)), ((80, 40), (0, 1))]:
        modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(3, seed=0)
        lam, m, n = discrete_spectrum(a, b, nx, ny, 3)[1]
        assert (m, n) == expected_second
        assert modes[1].cutoff_frequency_hz == pytest.approx(lam_to_hz(lam), rel=1e-10)


def test_validation_dossier_quick_run(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "benchmarks/validation_dossier.py"), "--quick", "--output", str(tmp_path)],
        capture_output=True, text=True, timeout=120, env=dict(os.environ, MPLBACKEND="Agg", PYTHONPATH=str(ROOT / "src")),
    )
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    worst = max(abs(row["eigensolver_rel_error"]) for s in data["mode_studies"] for row in s["modes"])
    assert worst < 1e-10
    assert (tmp_path / "report.md").read_text(encoding="utf-8").startswith("# OpenWave validation results")
    assert (tmp_path / "convergence.png").read_bytes().startswith(b"\x89PNG")
