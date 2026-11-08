"""Regenerate the OpenWave numerical validation dossier.

Usage (from the repository root, after ``python -m pip install -e .``)::

    python benchmarks/validation_dossier.py --output artifacts/validation

The script writes ``report.md`` (tables quoted in docs/VALIDATION.md),
``results.json`` (the same numbers, machine-readable) and ``convergence.png``.
Pass ``--quick`` for a small smoke run used by the test suite.

Every expected value here comes from a closed-form oracle that is independent
of the solver code:

* continuum TE(m,n) cutoffs of an ideal PEC rectangular guide,
  f_c = c0/2 * sqrt((m/a)^2 + (n/b)^2);
* the exact eigenpairs of the cell-centred Neumann five-point stencil,
  lambda = (2/dx sin(m pi/2nx))^2 + (2/dy sin(n pi/2ny))^2 with eigenvectors
  cos(m pi x/a) cos(n pi y/b) sampled at cell centres (derived in
  docs/VALIDATION.md).

The solver is only ever the thing being checked, never the reference.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
from pathlib import Path

import numpy as np
import scipy

from openwave.constants import C0
from openwave.operators import negative_neumann_laplacian_2d
from openwave.waveguide import RectangularWaveguide

SEED = 0
MM = 1e-3


# --------------------------------------------------------------------------
# Independent oracles
# --------------------------------------------------------------------------

def continuum_cutoff_hz(a: float, b: float, m: int, n: int) -> float:
    return C0 / 2.0 * math.hypot(m / a, n / b)


def discrete_eigenvalue(a: float, b: float, nx: int, ny: int, m: int, n: int) -> float:
    dx, dy = a / nx, b / ny
    return (2.0 / dx * math.sin(m * math.pi / (2 * nx))) ** 2 + (
        2.0 / dy * math.sin(n * math.pi / (2 * ny))
    ) ** 2


def discrete_cutoff_hz(a, b, nx, ny, m, n) -> float:
    return C0 * math.sqrt(discrete_eigenvalue(a, b, nx, ny, m, n)) / (2.0 * math.pi)


def predicted_relative_error(a, b, nx, ny, m, n) -> float:
    """Leading-order relative cutoff error, -(kx^4 dx^2 + ky^4 dy^2)/(24 kc^2)."""
    kx, ky = m * math.pi / a, n * math.pi / b
    dx, dy = a / nx, b / ny
    return -(kx**4 * dx**2 + ky**4 * dy**2) / (24.0 * (kx**2 + ky**2))


def discrete_spectrum(a, b, nx, ny, count):
    """Lowest ``count`` non-constant discrete eigenpairs as (lambda, m, n)."""
    pairs = [
        (discrete_eigenvalue(a, b, nx, ny, m, n), m, n)
        for m in range(nx) for n in range(ny) if (m, n) != (0, 0)
    ]
    pairs.sort()
    return pairs[:count]


def analytic_field(a, b, nx, ny, m, n) -> np.ndarray:
    x = (np.arange(nx) + 0.5) * a / nx
    y = (np.arange(ny) + 0.5) * b / ny
    return np.outer(np.cos(n * np.pi * y / b), np.cos(m * np.pi * x / a))


def group_degenerate(values, rtol=1e-9):
    """Index groups whose eigenvalues coincide to ``rtol``."""
    groups, current = [], [0]
    for i in range(1, len(values)):
        if abs(values[i] - values[current[0]]) <= rtol * abs(values[current[0]]):
            current.append(i)
        else:
            groups.append(current)
            current = [i]
    groups.append(current)
    return groups


def subspace_sine(basis_a: np.ndarray, basis_b: np.ndarray) -> float:
    """Sine of the largest principal angle from span(basis_a) to span(basis_b).

    Computed as ||(I - Qb Qb^T) Qa||_2, which stays accurate for tiny angles
    (1 - cos^2 would bottom out near sqrt(machine epsilon)). When basis_b has
    more columns this measures whether span(basis_a) lies inside span(basis_b).
    """
    qa, _ = np.linalg.qr(basis_a)
    qb, _ = np.linalg.qr(basis_b)
    return float(np.linalg.norm(qa - qb @ (qb.T @ qa), 2))


def _unit(vector: np.ndarray) -> np.ndarray:
    return vector / np.linalg.norm(vector)


# --------------------------------------------------------------------------
# Studies
# --------------------------------------------------------------------------

GEOMETRIES = [
    # name, width, height, mesh, purpose
    ("WR-90", 22.86, 10.16, (90, 40), "bundled example, aspect 2.25"),
    ("WR-90 rotated", 10.16, 22.86, (40, 90), "same guide, axes swapped"),
    ("WR-28", 7.112, 3.556, (80, 40), "aspect 2: TE20 and TE01 exactly degenerate"),
    ("Square", 10.0, 10.0, (48, 48), "aspect 1: TE10/TE01 and TE20/TE02 degenerate"),
    ("Near-degenerate", 20.0, 10.05, (80, 40), "TE01 and TE20 0.5% apart"),
]


def mode_study(name, width_mm, height_mm, mesh, count):
    a, b = width_mm * MM, height_mm * MM
    nx, ny = mesh
    guide = RectangularWaveguide(a, b, nx, ny)
    modes = guide.solve_te_modes(count, seed=SEED)
    # Look past the requested count: a degenerate group can straddle it.
    extended = discrete_spectrum(a, b, nx, ny, count + 4)
    oracle = extended[:count]
    operator = negative_neumann_laplacian_2d(nx, ny, a / nx, b / ny)

    fields = np.stack([_unit(mode.field.ravel()) for mode in modes], axis=1)
    gram = fields.T @ fields
    orthogonality = float(np.max(np.abs(gram - np.eye(count))))

    rows = []
    groups = group_degenerate([lam for lam, _, _ in extended])
    for full_group in groups:
        group = [i for i in full_group if i < count]
        if not group:
            continue
        labels = [(extended[i][1], extended[i][2]) for i in full_group]
        reference = np.stack(
            [_unit(analytic_field(a, b, nx, ny, m, n).ravel()) for m, n in labels], axis=1
        )
        shape_error = subspace_sine(fields[:, group], reference)
        for i in group:
            lam, m, n = oracle[i]
            mode = modes[i]
            vector = fields[:, i]
            residual = np.linalg.norm(operator @ vector - mode.cutoff_wavenumber**2 * vector)
            f_cont = continuum_cutoff_hz(a, b, m, n)
            f_disc = discrete_cutoff_hz(a, b, nx, ny, m, n)
            rows.append({
                "geometry": name, "mesh": [nx, ny], "solver_mode": mode.index,
                "oracle_label": "/".join(f"TE{p}{q}" for p, q in labels) if len(group) < len(full_group)
                else f"TE{m}{n}",
                "degenerate_with": len(full_group) - 1,
                "split_by_mode_count": len(group) < len(full_group),
                "solver_ghz": mode.cutoff_frequency_hz / 1e9,
                "discrete_oracle_ghz": f_disc / 1e9,
                "analytic_ghz": f_cont / 1e9,
                "eigensolver_rel_error": mode.cutoff_frequency_hz / f_disc - 1.0,
                "discretization_rel_error": mode.cutoff_frequency_hz / f_cont - 1.0,
                "predicted_rel_error": predicted_relative_error(a, b, nx, ny, m, n),
                "relative_residual": float(residual / lam),
                "shape_subspace_sine": shape_error,
            })
    return {"geometry": name, "width_mm": width_mm, "height_mm": height_mm,
            "mesh": [nx, ny], "orthogonality_max_offdiag": orthogonality, "modes": rows}


CONVERGENCE_LABELS = [(1, 0), (2, 0), (0, 1), (1, 1), (3, 0)]


def convergence_study(meshes):
    a, b = 22.86 * MM, 10.16 * MM
    results = []
    for nx, ny in meshes:
        modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(6, seed=SEED)
        oracle = discrete_spectrum(a, b, nx, ny, 6)
        by_label = {(m, n): modes[i].cutoff_frequency_hz for i, (_, m, n) in enumerate(oracle)}
        for m, n in CONVERGENCE_LABELS:
            numerical = by_label[(m, n)]
            results.append({"mesh": [nx, ny], "h_mm": 22.86 / nx, "label": f"TE{m}{n}",
                            "solver_ghz": numerical / 1e9,
                            "rel_error": numerical / continuum_cutoff_hz(a, b, m, n) - 1.0})
    for label in {row["label"] for row in results}:
        series = [row for row in results if row["label"] == label]
        for coarse, fine in zip(series, series[1:]):
            fine["observed_order"] = math.log(abs(coarse["rel_error"] / fine["rel_error"])) / math.log(
                coarse["h_mm"] / fine["h_mm"])
    return results


def seed_study(seeds):
    """Degenerate square guide: individual vectors may rotate, the subspace may not."""
    a = b = 10.0 * MM
    nx = ny = 48
    runs = []
    for seed in seeds:
        modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(2, seed=seed)
        runs.append((seed, modes))
    _, base = runs[0]
    base_basis = np.stack([_unit(m.field.ravel()) for m in base], axis=1)
    rows = []
    for seed, modes in runs:
        basis = np.stack([_unit(m.field.ravel()) for m in modes], axis=1)
        rows.append({
            "seed": seed,
            "mode1_ghz": modes[0].cutoff_frequency_hz / 1e9,
            "mode2_ghz": modes[1].cutoff_frequency_hz / 1e9,
            "mode1_abs_overlap_with_seed0": float(abs(basis[:, 0] @ base_basis[:, 0])),
            "pair_subspace_sine_vs_seed0": subspace_sine(basis, base_basis),
        })
    return rows


def unfavorable_cases():
    cases = []
    # 1. Ordering swap: a mesh that resolves x much more coarsely than y.
    a, b = 20.0 * MM, 10.05 * MM
    for nx, ny in [(10, 20), (80, 40)]:
        modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(3, seed=SEED)
        oracle = discrete_spectrum(a, b, nx, ny, 3)
        cases.append({
            "case": "near-degenerate ordering", "geometry": "20 x 10.05 mm", "mesh": [nx, ny],
            "solver_mode_2_label": f"TE{oracle[1][1]}{oracle[1][2]}",
            "solver_mode_2_ghz": modes[1].cutoff_frequency_hz / 1e9,
            "continuum_order": "TE10, TE01 (14.915 GHz), TE20 (14.990 GHz)",
        })
    # 2. Under-resolution: error of TE(m,0) versus cells per half-wavelength.
    a, b = 22.86 * MM, 10.16 * MM
    nx, ny = 12, 6
    count = 60  # 72 cells: nearly the whole discrete spectrum
    modes = RectangularWaveguide(a, b, nx, ny).solve_te_modes(count, seed=SEED)
    oracle = discrete_spectrum(a, b, nx, ny, count)
    for mode, (_, m, n) in zip(modes, oracle):
        if n == 0 and m in (1, 2, 3, 4, 6, 8):
            cases.append({
                "case": "under-resolution", "geometry": "WR-90", "mesh": [nx, ny],
                "label": f"TE{m}0", "cells_per_half_wavelength": nx / m,
                "rel_error": mode.cutoff_frequency_hz / continuum_cutoff_hz(a, b, m, 0) - 1.0,
            })
    return cases


INTERFACE_DEFAULTS = [
    ("GUI (fixed mesh)", 81, 41),
    ("Legacy CLI default", 81, 41),
    ("examples/wr90.json", 61, 31),
]


def interface_default_study():
    a, b = 22.86 * MM, 10.16 * MM
    rows = []
    for name, nx, ny in INTERFACE_DEFAULTS:
        f = discrete_cutoff_hz(a, b, nx, ny, 1, 0)
        rows.append({"interface": name, "mesh": [nx, ny], "te10_ghz": f / 1e9,
                     "rel_error": f / continuum_cutoff_hz(a, b, 1, 0) - 1.0})
    return rows


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def _e(value: float) -> str:
    return f"{value:.2e}"


def render_markdown(data: dict) -> str:
    lines = ["# OpenWave validation results", "",
             f"Generated with OpenWave source at `{data['environment']['git']}`, "
             f"Python {data['environment']['python']}, NumPy {data['environment']['numpy']}, "
             f"SciPy {data['environment']['scipy']}; ARPACK seed {SEED}.", ""]

    lines += ["## 1. Mode-by-mode checks", "",
              "| Geometry | Mesh | Solver mode | Oracle label | Solver GHz | Analytic GHz | "
              "Eigensolver rel. err. | Discretization rel. err. | Predicted | Residual | Shape sin θ |",
              "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for study in data["mode_studies"]:
        for row in study["modes"]:
            label = row["oracle_label"] + (
                " (deg., split by mode count)" if row["split_by_mode_count"]
                else " (deg.)" if row["degenerate_with"] else "")
            lines.append(
                f"| {row['geometry']} | {row['mesh'][0]}×{row['mesh'][1]} | {row['solver_mode']} | {label} | "
                f"{row['solver_ghz']:.6f} | {row['analytic_ghz']:.6f} | {_e(row['eigensolver_rel_error'])} | "
                f"{_e(row['discretization_rel_error'])} | {_e(row['predicted_rel_error'])} | "
                f"{_e(row['relative_residual'])} | {_e(row['shape_subspace_sine'])} |")
    lines += ["", "| Geometry | Max off-diagonal of field Gram matrix |", "| --- | ---: |"]
    lines += [f"| {s['geometry']} | {_e(s['orthogonality_max_offdiag'])} |" for s in data["mode_studies"]]

    lines += ["", "## 2. WR-90 mesh convergence", "",
              "| Mode | Mesh | h (mm) | Solver GHz | Rel. error | Observed order |",
              "| --- | --- | ---: | ---: | ---: | ---: |"]
    for label in [f"TE{m}{n}" for m, n in CONVERGENCE_LABELS]:
        for row in (r for r in data["convergence"] if r["label"] == label):
            order = f"{row['observed_order']:.3f}" if "observed_order" in row else "—"
            lines.append(f"| {label} | {row['mesh'][0]}×{row['mesh'][1]} | {row['h_mm']:.4f} | "
                         f"{row['solver_ghz']:.6f} | {_e(row['rel_error'])} | {order} |")

    lines += ["", "## 3. Seed sensitivity in a degenerate pair (10 × 10 mm, 48×48)", "",
              "| Seed | Mode 1 GHz | Mode 2 GHz | abs overlap of mode 1 with seed 0 | Pair subspace sin θ vs seed 0 |",
              "| ---: | ---: | ---: | ---: | ---: |"]
    for row in data["seeds"]:
        lines.append(f"| {row['seed']} | {row['mode1_ghz']:.9f} | {row['mode2_ghz']:.9f} | "
                     f"{row['mode1_abs_overlap_with_seed0']:.6f} | {_e(row['pair_subspace_sine_vs_seed0'])} |")

    lines += ["", "## 4. Unfavorable cases", "",
              "| Case | Geometry | Mesh | Detail | Value |", "| --- | --- | --- | --- | ---: |"]
    for row in data["unfavorable"]:
        mesh = f"{row['mesh'][0]}×{row['mesh'][1]}"
        if row["case"] == "near-degenerate ordering":
            lines.append(f"| {row['case']} | {row['geometry']} | {mesh} | solver mode 2 is "
                         f"{row['solver_mode_2_label']} | {row['solver_mode_2_ghz']:.4f} GHz |")
        else:
            lines.append(f"| {row['case']} | {row['geometry']} | {mesh} | {row['label']}, "
                         f"{row['cells_per_half_wavelength']:.1f} cells per half-wavelength | "
                         f"{_e(row['rel_error'])} |")

    lines += ["", "## 5. TE10 on each interface's default mesh (exact discrete oracle)", "",
              "| Interface | Mesh | TE10 GHz | Rel. error vs analytic |", "| --- | --- | ---: | ---: |"]
    for row in data["interfaces"]:
        lines.append(f"| {row['interface']} | {row['mesh'][0]}×{row['mesh'][1]} | "
                     f"{row['te10_ghz']:.6f} | {_e(row['rel_error'])} |")
    return "\n".join(lines) + "\n"


def save_convergence_plot(rows, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for m, n in CONVERGENCE_LABELS:
        series = [r for r in rows if r["label"] == f"TE{m}{n}"]
        ax.loglog([r["h_mm"] for r in series], [abs(r["rel_error"]) for r in series],
                  marker="o", label=f"TE{m}{n}")
    h = np.array(sorted({r["h_mm"] for r in rows}))
    anchor = 2.0 * max(abs(r["rel_error"]) for r in rows)  # offset so it does not hide data
    ax.loglog(h, anchor * (h / h.max()) ** 2, "k--", linewidth=1, label="slope 2")
    ax.set_xlabel("Cell size h = width / nx (mm)")
    ax.set_ylabel("|relative cutoff error|")
    ax.set_title("WR-90 cutoff convergence (cell-centred FD, dx ≈ dy)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _git_revision() -> str:
    import subprocess
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True, cwd=Path(__file__).resolve().parent, check=True)
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "src"], capture_output=True,
                               text=True, cwd=Path(__file__).resolve().parent, check=True)
        return out.stdout.strip() + ("+modified" if dirty.stdout.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build(quick: bool = False) -> dict:
    if quick:
        geometries = [(n, w, h, (m[0] // 2, m[1] // 2), p) for n, w, h, m, p in GEOMETRIES]
        meshes, seeds = [(18, 8), (36, 16)], [0, 1]
    else:
        geometries = GEOMETRIES
        meshes, seeds = [(18, 8), (36, 16), (72, 32), (144, 64)], [0, 1, 2, 3, 4]
    return {
        "environment": {"git": _git_revision(), "python": platform.python_version(),
                        "numpy": np.__version__, "scipy": scipy.__version__, "quick": quick},
        "mode_studies": [mode_study(n, w, h, m, 8) for n, w, h, m, _ in geometries],
        "convergence": convergence_study(meshes),
        "seeds": seed_study(seeds),
        "unfavorable": unfavorable_cases(),
        "interfaces": interface_default_study(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True, help="Directory to write into")
    parser.add_argument("--quick", action="store_true", help="Small meshes; smoke test only")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    data = build(args.quick)
    (args.output / "results.json").write_text(
        json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (args.output / "report.md").write_text(render_markdown(data), encoding="utf-8")
    save_convergence_plot(data["convergence"], args.output / "convergence.png")
    print(json.dumps({"status": "success", "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
