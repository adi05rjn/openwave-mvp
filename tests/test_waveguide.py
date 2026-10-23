import numpy as np
import pytest

from openwave.grid import StructuredGrid2D
from openwave.operators import negative_neumann_laplacian_2d
from openwave.waveguide import RectangularWaveguide


def test_cell_centred_grid_coordinates() -> None:
    grid = StructuredGrid2D(width=2.0, height=1.0, nx=4, ny=4)
    assert grid.dx == pytest.approx(0.5)
    assert grid.dy == pytest.approx(0.25)
    np.testing.assert_allclose(grid.x, [0.25, 0.75, 1.25, 1.75])
    np.testing.assert_allclose(grid.y, [0.125, 0.375, 0.625, 0.875])


def test_neumann_operator_preserves_constant_mode() -> None:
    grid = StructuredGrid2D(width=2.0, height=1.0, nx=7, ny=5)
    operator = negative_neumann_laplacian_2d(
        grid.nx, grid.ny, grid.dx, grid.dy
    )
    np.testing.assert_allclose(
        operator @ np.ones(grid.nx * grid.ny),
        np.zeros(grid.nx * grid.ny),
        atol=1e-12,
    )


def test_wr90_te10_cutoff_matches_analytic() -> None:
    guide = RectangularWaveguide(width=22.86e-3, height=10.16e-3, nx=61, ny=31)
    numerical = guide.solve_te_modes(count=1)[0].cutoff_frequency_hz
    analytic = guide.analytic_te_cutoff(1, 0)
    assert numerical == pytest.approx(analytic, rel=0.005)


def test_te10_cutoff_has_second_order_grid_convergence() -> None:
    errors = []
    for nx, ny in [(12, 6), (24, 12), (48, 24)]:
        guide = RectangularWaveguide(22.86e-3, 10.16e-3, nx=nx, ny=ny)
        numerical = guide.solve_te_modes(count=1)[0].cutoff_frequency_hz
        analytic = guide.analytic_te_cutoff(1, 0)
        errors.append(abs(numerical / analytic - 1.0))

    assert errors[1] < errors[0] / 3.5
    assert errors[2] < errors[1] / 3.5


def test_solver_rejects_too_many_modes() -> None:
    guide = RectangularWaveguide(22.86e-3, 10.16e-3, nx=4, ny=4)
    with pytest.raises(ValueError, match="fewer than"):
        guide.solve_te_modes(count=15)


def test_propagation_constant_is_real_above_cutoff() -> None:
    guide = RectangularWaveguide(width=22.86e-3, height=10.16e-3)
    cutoff = guide.analytic_te_cutoff(1, 0)
    beta = guide.propagation_constant(1.5 * cutoff, cutoff)
    assert beta.real > 0
    assert abs(beta.imag) < 1e-12
