"""Cell-centred structured 2-D grid utilities.

Each unknown is located at a cell centre. This matches the symmetric
finite-volume Neumann stencil used by the waveguide eigenmode operator.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class StructuredGrid2D:
    width: float
    height: float
    nx: int
    ny: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Grid dimensions must be positive")
        if self.nx < 4 or self.ny < 4:
            raise ValueError("nx and ny must each be at least 4")

    @property
    def dx(self) -> float:
        return self.width / self.nx

    @property
    def dy(self) -> float:
        return self.height / self.ny

    @property
    def x(self) -> np.ndarray:
        return (np.arange(self.nx) + 0.5) * self.dx

    @property
    def y(self) -> np.ndarray:
        return (np.arange(self.ny) + 0.5) * self.dy
