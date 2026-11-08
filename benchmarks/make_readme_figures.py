"""Regenerate the README images from the real solver and the real GUI.

Usage, from the repository root after ``python -m pip install -e .``::

    python benchmarks/make_readme_figures.py                    # modes.png, convergence.png
    xvfb-run -a python benchmarks/make_readme_figures.py --gui  # also gui.png, gui.gif

Nothing here is drawn by hand. ``modes.png`` is computed with the same solver,
mesh and colour map the desktop app uses; ``convergence.png`` comes from the
validation dossier; ``gui.png`` and ``gui.gif`` are screenshots of the actual
Tk window, which is why ``--gui`` needs Tkinter and a display (a virtual one is
fine). Under a virtual display there is no window manager, so no title bar.
The GUI does not fix the eigenvector sign, so red and blue may swap between
regenerations of gui.png and gui.gif; modes.png applies a fixed sign convention.

Each mode panel is labelled with an analytical TE(m,n) name only after checking
that the solver's cutoff agrees with that mode's analytical cutoff to 0.1 %.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from openwave.constants import C0  # noqa: E402
from openwave.gui import GUI_MESH  # noqa: E402
from openwave.waveguide import RectangularWaveguide  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "images"
WIDTH_M, HEIGHT_M = 22.86e-3, 10.16e-3  # WR-90, the app's starting example
LABEL_TOLERANCE = 1e-3


def te_label(cutoff_hz: float) -> str:
    """Analytical TE(m,n) name for a cutoff, refusing anything not clearly matched."""
    candidates = sorted(
        (abs(cutoff_hz / (C0 / 2 * math.hypot(m / WIDTH_M, n / HEIGHT_M)) - 1), m, n)
        for m in range(4) for n in range(4) if (m, n) != (0, 0)
    )
    error, m, n = candidates[0]
    runner_up = candidates[1][0]
    if error > LABEL_TOLERANCE or runner_up < 10 * error:
        raise SystemExit(f"cannot label cutoff {cutoff_hz / 1e9:.4f} GHz unambiguously")
    return f"TE{m}{n}"


def modes_figure(out_dir: Path) -> None:
    nx, ny = GUI_MESH
    guide = RectangularWaveguide(WIDTH_M, HEIGHT_M, nx, ny)
    modes = guide.solve_te_modes(4, seed=0)
    labels = [te_label(m.cutoff_frequency_hz) for m in modes]
    if len(set(labels)) != len(labels):
        raise SystemExit(f"duplicate labels {labels}")

    fig, axes = plt.subplots(2, 2, figsize=(9.2, 4.6), sharex=True, sharey=True,
                             layout="constrained")
    heatmap = None
    for ax, mode, label in zip(axes.flat, modes, labels):
        field = mode.field
        # Same sign convention as the JSON bundle: first sample over 0.5 is positive.
        first = field.ravel()[abs(field.ravel()) > 0.5][0]
        field = field if first > 0 else -field
        heatmap = ax.pcolormesh(guide.grid.x * 1e3, guide.grid.y * 1e3, field,
                                shading="auto", cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_title(f"Mode {mode.index} · {mode.cutoff_frequency_hz / 1e9:.3f} GHz · {label}",
                     fontsize=10)
        ax.set_aspect("equal", adjustable="box")
    for ax in axes[1]:
        ax.set_xlabel("Width direction (mm)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Height direction (mm)")
    fig.suptitle(f"WR-90 (22.86 × 10.16 mm): first four scalar TE modes, {nx}×{ny} cells",
                 fontsize=11.5)
    fig.colorbar(heatmap, ax=axes, shrink=0.9,
                 label="Relative magnetic field H_z (sign only, not heat or power)")
    fig.savefig(out_dir / "modes.png", dpi=140, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print("modes.png:", ", ".join(f"mode {m.index} = {lab}" for m, lab in zip(modes, labels)))


def convergence_figure(out_dir: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import validation_dossier as dossier

    rows = dossier.convergence_study([(18, 8), (36, 16), (72, 32), (144, 64)])
    dossier.save_convergence_plot(rows, out_dir / "convergence.png")
    print("convergence.png written")


def gui_screenshots(out_dir: Path) -> None:
    import tkinter as tk
    from tkinter import ttk

    from PIL import Image, ImageGrab

    from openwave import gui

    frames: list[Image.Image] = []
    failure: list[BaseException] = []

    def settle(root, seconds: float) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            root.update()
            time.sleep(0.02)

    def walk(widget):
        yield widget
        for child in widget.winfo_children():
            yield from walk(child)

    def drive(root) -> None:
        try:
            widgets = list(walk(root))
            selector = next(w for w in widgets if isinstance(w, ttk.Combobox))
            exit_button = next(w for w in widgets
                               if isinstance(w, ttk.Button) and str(w.cget("text")) == "Exit")
            settle(root, 1.0)
            for index in range(len(selector.cget("values"))):
                selector.current(index)
                selector.event_generate("<<ComboboxSelected>>")
                settle(root, 0.6)
                x, y = root.winfo_rootx(), root.winfo_rooty()
                box = (x, y, x + root.winfo_width(), y + root.winfo_height())
                frames.append(ImageGrab.grab(bbox=box).convert("RGB"))
            exit_button.invoke()
        except BaseException as exc:  # report after the window is gone
            failure.append(exc)
            root.destroy()

    class DrivenTk(tk.Tk):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.after(1500, lambda: drive(self))
            self.after(60_000, self.destroy)  # watchdog

    with patch("tkinter.Tk", DrivenTk):
        gui.main()
    if failure:
        raise failure[0]
    if len(frames) != 4:
        raise SystemExit(f"expected 4 screenshots, got {len(frames)}")

    frames[0].save(out_dir / "gui.png", optimize=True)
    palette = [f.convert("P", palette=Image.Palette.ADAPTIVE, colors=128) for f in frames]
    palette[0].save(out_dir / "gui.gif", save_all=True, append_images=palette[1:],
                    duration=1800, loop=0, optimize=True, disposal=1)
    print(f"gui.png and gui.gif written ({frames[0].size[0]}×{frames[0].size[1]})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--gui", action="store_true",
                        help="also screenshot the real desktop app (needs Tk and a display)")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    modes_figure(args.output)
    convergence_figure(args.output)
    if args.gui:
        gui_screenshots(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
