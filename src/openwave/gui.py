"""Beginner-friendly desktop GUI for rectangular waveguide TE modes."""

from __future__ import annotations

import math

from .plotting import save_mode_plot
from .waveguide import RectangularWaveguide


DEFAULT_MODE_COUNT = 4


def validate_inputs(
    width_text: str, height_text: str, modes_text: str = "4"
) -> tuple[float, float, int]:
    """Check dimensions in millimetres; retain a mode-count hook for tests."""
    try:
        width = float(width_text)
        height = float(height_text)
    except ValueError as exc:
        raise ValueError("Enter width and height as numbers in millimetres.") from exc
    if not all(math.isfinite(value) and value > 0 for value in (width, height)):
        raise ValueError("Width and height must be positive numbers.")
    try:
        count = int(modes_text)
    except ValueError as exc:
        raise ValueError("Mode count must be a whole number.") from exc
    if not 1 <= count <= 12:
        raise ValueError("Mode count must be between 1 and 12.")
    return width, height, count


def cutoff_explanation(cutoff_frequency_hz: float) -> str:
    """Explain the meaning of a cutoff frequency using student-facing language."""
    return (
        f"Cutoff: {cutoff_frequency_hz / 1e9:.3f} GHz. "
        "Below this frequency, this mode cannot travel down the waveguide."
    )


def main() -> None:
    """Launch a single-screen experiment; keep technical settings out of sight."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
    except ImportError as exc:
        raise SystemExit("Tkinter is required (Ubuntu/Debian: sudo apt install python3-tk)") from exc

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise SystemExit("A graphical desktop session is required to run openwave-gui") from exc
    root.title("OpenWave — Explore waveguide modes")
    root.minsize(720, 580)

    width_var = tk.StringVar(value="22.86")
    height_var = tk.StringVar(value="10.16")
    cutoff_var = tk.StringVar(value="The cutoff is the minimum frequency at which a mode can travel.")
    status_var = tk.StringVar(value="Loading the example waveguide…")
    result = None
    modes = []

    heading = ttk.Frame(root, padding=(14, 12, 14, 4))
    heading.pack(fill="x")
    ttk.Label(
        heading, text="Explore waveguide modes", font=("TkDefaultFont", 16, "bold")
    ).pack(anchor="w")
    ttk.Label(
        heading,
        text="Change the size of the waveguide and see how its magnetic-field patterns change.",
        wraplength=680,
    ).pack(anchor="w", pady=(4, 0))

    controls = ttk.Frame(root, padding=(14, 8))
    controls.pack(fill="x")
    for col, (title, value) in enumerate((
        ("Width (mm)", width_var),
        ("Height (mm)", height_var),
    )):
        ttk.Label(controls, text=title).grid(row=0, column=col, sticky="w")
        ttk.Entry(controls, textvariable=value, width=15).grid(
            row=1, column=col, sticky="ew", padx=(0, 12), pady=(4, 0)
        )
        controls.columnconfigure(col, weight=1)

    figure = Figure(figsize=(7, 4), dpi=100)
    canvas = FigureCanvasTkAgg(figure, master=root)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=14, pady=(4, 8))

    def display_mode(_event=None) -> None:
        if result is None or not modes:
            return
        mode = modes[selector.current()]
        figure.clear()
        axes = figure.add_subplot(111)
        heatmap = axes.pcolormesh(
            result.grid.x * 1e3, result.grid.y * 1e3, mode.field,
            shading="auto", cmap="RdBu_r", vmin=-1, vmax=1,
        )
        axes.set(
            xlabel="Width direction (mm)",
            ylabel="Height direction (mm)",
            title=f"Mode {mode.index} · {mode.cutoff_frequency_hz / 1e9:.3f} GHz cutoff",
        )
        axes.set_aspect("equal", adjustable="box")
        figure.colorbar(heatmap, ax=axes, label="Relative magnetic field (H_z)")
        figure.tight_layout()
        canvas.draw_idle()
        cutoff_var.set(cutoff_explanation(mode.cutoff_frequency_hz))

    def run_simulation(_event=None) -> None:
        nonlocal result, modes
        try:
            width, height, count = validate_inputs(
                width_var.get(), height_var.get(), str(DEFAULT_MODE_COUNT)
            )
            candidate = RectangularWaveguide(width * 1e-3, height * 1e-3)
            computed = candidate.solve_te_modes(count)
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror("Check dimensions", str(exc), parent=root)
            status_var.set("Check the dimensions and try again.")
            return
        result, modes = candidate, computed
        selector["values"] = [
            f"Mode {mode.index} — {mode.cutoff_frequency_hz / 1e9:.3f} GHz"
            for mode in modes
        ]
        selector.current(0)
        selector["state"] = "readonly"
        save_button["state"] = "normal"
        status_var.set("Try changing the width or height, then press Update.")
        display_mode()

    def save_png() -> None:
        if result is None or not modes:
            return
        target = filedialog.asksaveasfilename(
            parent=root, title="Save mode plot", defaultextension=".png",
            filetypes=[("PNG image", "*.png")], initialfile="openwave-mode.png",
        )
        if target:
            try:
                save_mode_plot(result.grid, modes[selector.current()], target)
            except OSError as exc:
                messagebox.showerror("Save failed", str(exc), parent=root)

    def close_app(_event=None) -> None:
        root.quit()
        root.destroy()

    ttk.Button(controls, text="Update", command=run_simulation).grid(
        row=1, column=2, padx=(4, 0)
    )
    actions = ttk.Frame(root, padding=(14, 0, 14, 4))
    actions.pack(fill="x")
    ttk.Label(actions, text="Show pattern:").pack(side="left", padx=(0, 8))
    selector = ttk.Combobox(actions, width=28, state="disabled")
    selector.pack(side="left", padx=(0, 12))
    selector.bind("<<ComboboxSelected>>", display_mode)
    save_button = ttk.Button(actions, text="Save image", command=save_png, state="disabled")
    save_button.pack(side="left")
    ttk.Button(actions, text="Exit", command=close_app).pack(side="right")

    explanation = ttk.Frame(root, padding=(14, 6, 14, 4))
    explanation.pack(fill="x")
    ttk.Label(explanation, textvariable=cutoff_var, wraplength=680).pack(anchor="w")
    ttk.Label(
        explanation,
        text="Red and blue indicate opposite signs of the magnetic field (H_z), not heat or power.",
        wraplength=680,
    ).pack(anchor="w", pady=(4, 0))
    ttk.Label(root, textvariable=status_var, padding=(14, 2, 14, 10)).pack(fill="x")

    root.bind("<Return>", run_simulation)
    root.bind("<Escape>", close_app)
    root.protocol("WM_DELETE_WINDOW", close_app)
    root.after_idle(run_simulation)
    root.mainloop()


if __name__ == "__main__":
    main()
