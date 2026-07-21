"""Sparse differential operators for modal analysis."""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix, eye, kron


def neumann_laplacian_1d(n: int, spacing: float) -> csr_matrix:
    """Return a second-derivative matrix with homogeneous Neumann boundaries.

    The mirrored ghost-point discretization preserves the constant null mode.
    """
    if n < 3:
        raise ValueError("n must be at least 3")
    if spacing <= 0:
        raise ValueError("spacing must be positive")

    matrix = np.zeros((n, n), dtype=float)
    scale = 1.0 / spacing**2

    for i in range(1, n - 1):
        matrix[i, i - 1] = scale
        matrix[i, i] = -2.0 * scale
        matrix[i, i + 1] = scale

    # Symmetric finite-volume form at the boundary. The half control
    # volumes produce a graph-Laplacian stencil and preserve the constant mode.
    matrix[0, 0] = -1.0 * scale
    matrix[0, 1] = 1.0 * scale
    matrix[-1, -2] = 1.0 * scale
    matrix[-1, -1] = -1.0 * scale
    return csr_matrix(matrix)


def negative_neumann_laplacian_2d(nx: int, ny: int, dx: float, dy: float) -> csr_matrix:
    """Build -∇² on a tensor-product grid with Neumann boundaries."""
    lx = neumann_laplacian_1d(nx, dx)
    ly = neumann_laplacian_1d(ny, dy)
    return -(kron(eye(ny, format="csr"), lx) + kron(ly, eye(nx, format="csr")))
