"""Drive the real Tk desktop GUI through the README walkthrough (issue #6, P0).

Skipped unless Tkinter and a display are available. In CI it runs under Xvfb:

    xvfb-run -a python -m pytest -q tests/test_gui_session.py

The GUI code is not modified or mocked: widgets are found by walking the real
window, and only the native save dialog and error box are patched (they would
block waiting for a person).
"""
from __future__ import annotations

import os
import time
from unittest.mock import patch

import pytest

tk = pytest.importorskip("tkinter")
if not os.environ.get("DISPLAY") and os.name == "posix" and not os.environ.get("WAYLAND_DISPLAY"):
    pytest.skip("no display; run under xvfb-run", allow_module_level=True)

from tkinter import ttk

from openwave import gui

# Written out, not imported, so a silent change to the GUI mesh fails here.
GUI_MESH = (81, 41)
HALF_DIGIT = 5.0001e-4  # labels show 3 decimals of GHz
UPDATE_BUDGET_SECONDS = 5.0  # generous; measured ~0.2 s on the development machine


def discrete_cutoffs_ghz(width_mm, height_mm, nx, ny, count=4):
    """Exact discrete spectrum of the cell-centred stencil (docs/VALIDATION.md)."""
    import math
    c0 = 299_792_458.0
    a, b = width_mm * 1e-3, height_mm * 1e-3
    lams = sorted(
        (2 * nx / a * math.sin(m * math.pi / (2 * nx))) ** 2
        + (2 * ny / b * math.sin(n * math.pi / (2 * ny))) ** 2
        for m in range(nx) for n in range(ny) if (m, n) != (0, 0)
    )[:count]
    return [c0 * math.sqrt(lam) / (2 * math.pi) / 1e9 for lam in lams]


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


def _labels(values):
    return [float(text.split("—")[1].split("GHz")[0]) for text in values]


def test_readme_walkthrough_in_real_window(tmp_path):
    log: dict = {}

    def drive(root):
        try:
            widgets = list(_walk(root))
            entries = [w for w in widgets if isinstance(w, ttk.Entry) and not isinstance(w, ttk.Combobox)]
            buttons = {str(w.cget("text")): w for w in widgets if isinstance(w, ttk.Button)}
            selector = next(w for w in widgets if isinstance(w, ttk.Combobox))
            log["initial"] = list(selector.cget("values"))
            log["save_enabled"] = str(buttons["Save image"].cget("state"))

            # README step 3: change width to 30 mm and press Update.
            entries[0].delete(0, "end")
            entries[0].insert(0, "30")
            start = time.perf_counter()
            buttons["Update"].invoke()
            log["update_seconds"] = time.perf_counter() - start
            log["after_update"] = list(selector.cget("values"))

            # README step 5: choose another pattern, then save it.
            selector.current(2)
            selector.event_generate("<<ComboboxSelected>>")
            root.update()
            log["explanation"] = [str(w.cget("text")) for w in widgets if isinstance(w, ttk.Label)]
            target = tmp_path / "mode3.png"
            with patch("tkinter.filedialog.asksaveasfilename", return_value=str(target)):
                buttons["Save image"].invoke()
            log["png"] = target.read_bytes()[:8] if target.exists() else b""

            # Invalid input must report an error and keep the previous result.
            entries[0].delete(0, "end")
            entries[0].insert(0, "-1")
            with patch("tkinter.messagebox.showerror") as error_box:
                buttons["Update"].invoke()
            log["error_called"] = error_box.called
            log["after_error"] = list(selector.cget("values"))

            buttons["Exit"].invoke()
            log["exited"] = True
        except Exception as exc:  # surface in the test instead of hanging mainloop
            log["error"] = exc
            root.quit()
            root.destroy()

    class DrivenTk(tk.Tk):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.after(500, lambda: drive(self))  # after the initial example has rendered
            self.after(60_000, self.quit)  # watchdog

    with patch("tkinter.Tk", DrivenTk):
        gui.main()

    assert "error" not in log, log.get("error")
    assert log.get("exited") is True
    assert log["initial"] and log["save_enabled"] == "normal"
    assert _labels(log["initial"]) == pytest.approx(discrete_cutoffs_ghz(22.86, 10.16, *GUI_MESH), abs=HALF_DIGIT)
    assert _labels(log["after_update"]) == pytest.approx(discrete_cutoffs_ghz(30, 10.16, *GUI_MESH), abs=HALF_DIGIT)
    assert log["update_seconds"] < UPDATE_BUDGET_SECONDS
    mode3 = discrete_cutoffs_ghz(30, 10.16, *GUI_MESH)[2]
    assert any(f"Cutoff: {mode3:.3f} GHz" in text for text in log["explanation"])
    assert any("not heat or power" in text for text in log["explanation"])
    assert log["png"] == b"\x89PNG\r\n\x1a\n"
    assert log["error_called"] and log["after_error"] == log["after_update"]
