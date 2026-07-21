"""Structured 2-D grid utilities."""

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
        return self.width / (self.nx - 1)

    @property
    def dy(self) -> float:
        return self.height / (self.ny - 1)

    @property
    def x(self) -> np.ndarray:
        return np.linspace(0.0, self.width, self.nx)

    @property
    def y(self) -> np.ndarray:
        return np.linspace(0.0, self.height, self.ny)
