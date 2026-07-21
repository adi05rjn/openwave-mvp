"""Command-line entry point."""

from __future__ import annotations

import argparse

from .plotting import save_mode_plot
from .waveguide import RectangularWaveguide


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenWave rectangular-waveguide modal solver")
    parser.add_argument("--width-mm", type=float, default=22.86, help="Waveguide width in millimetres")
    parser.add_argument("--height-mm", type=float, default=10.16, help="Waveguide height in millimetres")
    parser.add_argument("--nx", type=int, default=81)
    parser.add_argument("--ny", type=int, default=41)
    parser.add_argument("--modes", type=int, default=4)
    parser.add_argument("--plot", default="artifacts/mode1.png")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    guide = RectangularWaveguide(args.width_mm * 1e-3, args.height_mm * 1e-3, args.nx, args.ny)
    modes = guide.solve_te_modes(args.modes)
    print("mode, cutoff_GHz")
    for mode in modes:
        print(f"{mode.index}, {mode.cutoff_frequency_hz / 1e9:.6f}")
    save_mode_plot(guide.grid, modes[0], args.plot)
    print(f"Saved first-mode field plot to {args.plot}")


if __name__ == "__main__":
    main()
