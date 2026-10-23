"""Minimal desktop GUI for the rectangular PEC waveguide solver."""

from __future__ import annotations

import math

from .plotting import save_mode_plot
from .waveguide import RectangularWaveguide


def validate_inputs(width_text: str, height_text: str, modes_text: str) -> tuple[float, float, int]:
    """Validate dimensions in mm and a modest number of modes."""
    try:
        width = float(width_text)
        height = float(height_text)
        count = int(modes_text)
    except ValueError as exc:
        raise ValueError("Use numeric dimensions and a whole-number mode count") from exc
    if not all(math.isfinite(value) and value > 0 for value in (width, height)):
        raise ValueError("Width and height must be finite positive numbers")
    if not 1 <= count <= 12:
        raise ValueError("Mode count must be between 1 and 12")
    return width, height, count


def main() -> None:
    """Launch the optional GUI without changing the solver or CLI."""
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
    root.title("OpenWave — rectangular waveguide")
    root.minsize(720, 540)

    width_var = tk.StringVar(value="22.86")
    height_var = tk.StringVar(value="10.16")
    count_var = tk.StringVar(value="4")
    status_var = tk.StringVar(value="Ready — enter dimensions and run")
    result = None
    modes = []

    controls = ttk.Frame(root, padding=12)
    controls.pack(fill="x")
    for col, (title, value) in enumerate((
        ("Width (mm)", width_var),
        ("Height (mm)", height_var),
        ("Modes", count_var),
    )):
        ttk.Label(controls, text=title).grid(row=0, column=col, sticky="w")
        ttk.Entry(controls, textvariable=value, width=12).grid(
            row=1, column=col, sticky="ew", padx=(0, 12), pady=(4, 0)
        )
        controls.columnconfigure(col, weight=1)

    figure = Figure(figsize=(7, 4), dpi=100)
    canvas = FigureCanvasTkAgg(figure, master=root)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=8)

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
        axes.set(xlabel="x (mm)", ylabel="y (mm)",
                 title=f"TE scalar mode {mode.index}: {mode.cutoff_frequency_hz / 1e9:.4f} GHz")
        figure.colorbar(heatmap, ax=axes, label="Normalized Hz")
        figure.tight_layout()
        canvas.draw_idle()

    def run_simulation(_event=None) -> None:
        nonlocal result, modes
        try:
            width, height, count = validate_inputs(
                width_var.get(), height_var.get(), count_var.get()
            )
            candidate = RectangularWaveguide(width * 1e-3, height * 1e-3)
            computed = candidate.solve_te_modes(count)
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror("Simulation failed", str(exc), parent=root)
            status_var.set("Simulation failed")
            return
        result, modes = candidate, computed
        selector["values"] = [
            f"Mode {mode.index} — {mode.cutoff_frequency_hz / 1e9:.4f} GHz" for mode in modes
        ]
        selector.current(0)
        selector["state"] = "readonly"
        save_button["state"] = "normal"
        status_var.set(f"Solved {len(modes)} TE modes on an 81 × 41 grid")
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

    ttk.Button(controls, text="Run", command=run_simulation).grid(row=1, column=3)
    actions = ttk.Frame(root, padding=(12, 0, 12, 8))
    actions.pack(fill="x")
    selector = ttk.Combobox(actions, width=34, state="disabled")
    selector.pack(side="left", padx=(0, 12))
    selector.bind("<<ComboboxSelected>>", display_mode)
    save_button = ttk.Button(actions, text="Save PNG", command=save_png, state="disabled")
    save_button.pack(side="left")
    ttk.Label(root, textvariable=status_var, padding=(12, 0, 12, 10)).pack(fill="x")
    root.bind("<Return>", run_simulation)
    root.mainloop()


if __name__ == "__main__":
    main()
