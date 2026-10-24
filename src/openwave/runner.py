"""Headless application service and artifact writer around the existing solver."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import metadata
from pathlib import Path
import platform
import tempfile

import numpy as np
import scipy

from .experiment import validate_experiment
from .waveguide import RectangularWaveguide


def json_bytes(value) -> bytes:
    import json
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ExperimentResult:
    experiment: dict
    modes: list[dict]
    fields: np.ndarray
    x_m: np.ndarray
    y_m: np.ndarray


def execute_experiment(document: object) -> ExperimentResult:
    """Validate and solve in memory; no GUI, plotting, or output-path policy."""
    experiment = validate_experiment(document)
    geometry, mesh, settings = (experiment[key] for key in ("geometry", "mesh", "solver"))
    guide = RectangularWaveguide(
        geometry["width_mm"] * 1e-3, geometry["height_mm"] * 1e-3,
        mesh["nx"], mesh["ny"],
    )
    solved = guide.solve_te_modes(settings["modes"], seed=settings["seed"])
    fields = np.stack([mode.field for mode in solved])
    if not np.isfinite(fields).all():
        raise RuntimeError("Solver produced non-finite fields")
    # Eigenvectors have arbitrary sign. Choose the first substantial sample positive.
    for field in fields:
        anchor = field.flat[np.flatnonzero(np.abs(field.ravel()) > 0.5)[0]]
        if anchor < 0:
            field *= -1
    modes = [
        {"index": mode.index, "cutoff_wavenumber_rad_per_m": mode.cutoff_wavenumber,
         "cutoff_frequency_hz": float(mode.cutoff_frequency_hz)}
        for mode in solved
    ]
    if not np.isfinite(fields).all() or not all(
        np.isfinite(list(mode.values())).all() for mode in modes
    ):
        raise RuntimeError("Solver produced non-finite results")
    return ExperimentResult(experiment, modes, fields, guide.grid.x, guide.grid.y)


def _provenance() -> dict:
    from . import constants, grid, operators, waveguide
    modules = (constants, grid, operators, waveguide)
    try:
        version = metadata.version("openwave-mvp")
    except metadata.PackageNotFoundError:
        version = "0.1.0+source"
    return {
        "openwave": version, "python": platform.python_version(),
        "numpy": np.__version__, "scipy": scipy.__version__,
        "solver": "scalar-te-finite-difference-v1",
        "source_sha256": {path.name: _sha256(path.read_bytes())
                          for path in [*(Path(module.__file__) for module in modules), Path(__file__)]},
    }


def run_experiment(document: object, output_dir: str | Path) -> dict:
    """Publish a complete bundle in a new directory; never overwrite a previous run."""
    experiment = validate_experiment(document)
    target = Path(output_dir)
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Output directory already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    result = execute_experiment(experiment)
    with tempfile.TemporaryDirectory(prefix=".openwave-", dir=target.parent) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir()
        (staging / "experiment.json").write_bytes(json_bytes(result.experiment))
        for name, array in (("fields.npy", result.fields), ("x_m.npy", result.x_m), ("y_m.npy", result.y_m)):
            np.save(staging / name, array, allow_pickle=False)
        report = {
            "result_version": "1.0", "status": "success",
            "experiment_sha256": _sha256(json_bytes(result.experiment)),
            "provenance": _provenance(), "modes": result.modes,
            "field": {"quantity": "relative_H_z", "units": "dimensionless",
                      "normalization": "max_abs=1; first abs>0.5 sample positive",
                      "axes": ["mode", "y", "x"], "shape": list(result.fields.shape)},
            "artifacts": {p.name: {"sha256": _sha256(p.read_bytes()), "bytes": p.stat().st_size}
                          for p in sorted(staging.iterdir())},
        }
        (staging / "results.json").write_bytes(json_bytes(report))
        # A populated destination cannot be replaced by rename. Recheck for empty dirs too.
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Output directory already exists: {target}")
        staging.rename(target)
    return report
