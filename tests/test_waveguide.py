import pytest

from openwave.waveguide import RectangularWaveguide


def test_wr90_te10_cutoff_matches_analytic() -> None:
    guide = RectangularWaveguide(width=22.86e-3, height=10.16e-3, nx=61, ny=31)
    numerical = guide.solve_te_modes(count=1)[0].cutoff_frequency_hz
    analytic = guide.analytic_te_cutoff(1, 0)
    assert numerical == pytest.approx(analytic, rel=0.04)


def test_propagation_constant_is_real_above_cutoff() -> None:
    guide = RectangularWaveguide(width=22.86e-3, height=10.16e-3)
    cutoff = guide.analytic_te_cutoff(1, 0)
    beta = guide.propagation_constant(1.5 * cutoff, cutoff)
    assert beta.real > 0
    assert abs(beta.imag) < 1e-12
