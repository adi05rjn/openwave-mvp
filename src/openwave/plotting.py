"""Plotting helpers."""

from pathlib import Path

import matplotlib.pyplot as plt

from .grid import StructuredGrid2D
from .waveguide import Mode


def save_mode_plot(grid: StructuredGrid2D, mode: Mode, output: str | Path) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4))
    plt.pcolormesh(grid.x * 1e3, grid.y * 1e3, mode.field, shading="auto")
    plt.xlabel("x (mm)")
    plt.ylabel("y (mm)")
    plt.title(f"TE scalar mode {mode.index}: fc={mode.cutoff_frequency_hz / 1e9:.4f} GHz")
    plt.colorbar(label="Normalized Hz")
    plt.tight_layout()
    plt.savefig(output, dpi=180)
    plt.close()
