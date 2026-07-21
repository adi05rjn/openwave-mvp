"""Rectangular waveguide modal solver."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse.linalg import eigsh

from .constants import C0
from .grid import StructuredGrid2D
from .operators import negative_neumann_laplacian_2d


@dataclass(frozen=True)
class Mode:
    index: int
    cutoff_wavenumber: float
    cutoff_frequency_hz: float
    field: np.ndarray


class RectangularWaveguide:
    """PEC rectangular waveguide using a scalar TE-mode eigenproblem.

    The MVP solves -∇t² Hz = kc² Hz with homogeneous Neumann boundaries.
    This is suitable for learning, verification, and architecture prototyping;
    it is not yet a full-vector edge-element FEM implementation.
    """

    def __init__(self, width: float, height: float, nx: int = 81, ny: int = 41):
        self.grid = StructuredGrid2D(width=width, height=height, nx=nx, ny=ny)

    def analytic_te_cutoff(self, m: int, n: int, eps_r: float = 1.0, mu_r: float = 1.0) -> float:
        if m < 0 or n < 0 or (m == 0 and n == 0):
            raise ValueError("TE mode indices must be non-negative and not both zero")
        kc = np.sqrt((m * np.pi / self.grid.width) ** 2 + (n * np.pi / self.grid.height) ** 2)
        return C0 * kc / (2.0 * np.pi * np.sqrt(eps_r * mu_r))

    def solve_te_modes(self, count: int = 6, eps_r: float = 1.0, mu_r: float = 1.0) -> list[Mode]:
        if count < 1:
            raise ValueError("count must be positive")
        if eps_r <= 0 or mu_r <= 0:
            raise ValueError("Material parameters must be positive")

        operator = negative_neumann_laplacian_2d(
            self.grid.nx, self.grid.ny, self.grid.dx, self.grid.dy
        )

        # Request one extra eigenpair because the Neumann problem has a zero mode.
        eigenvalues, eigenvectors = eigsh(operator, k=count + 1, which="SM")
        order = np.argsort(eigenvalues)
        eigenvalues = np.maximum(eigenvalues[order], 0.0)
        eigenvectors = eigenvectors[:, order]

        modes: list[Mode] = []
        for value, vector in zip(eigenvalues, eigenvectors.T, strict=True):
            if value < 1e-8:
                continue
            kc = float(np.sqrt(value))
            cutoff = C0 * kc / (2.0 * np.pi * np.sqrt(eps_r * mu_r))
            field = vector.reshape((self.grid.ny, self.grid.nx))
            field /= np.max(np.abs(field))
            modes.append(Mode(len(modes) + 1, kc, cutoff, field))
            if len(modes) == count:
                break
        return modes

    def propagation_constant(self, frequency_hz: float, cutoff_frequency_hz: float, eps_r: float = 1.0, mu_r: float = 1.0) -> complex:
        if frequency_hz <= 0:
            raise ValueError("frequency_hz must be positive")
        k = 2.0 * np.pi * frequency_hz * np.sqrt(eps_r * mu_r) / C0
        kc = 2.0 * np.pi * cutoff_frequency_hz * np.sqrt(eps_r * mu_r) / C0
        return complex(np.sqrt(k**2 - kc**2 + 0j))
