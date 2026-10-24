"""Versioned experiment contract, independent of numerical and UI libraries."""
from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
import json
import math
from pathlib import Path


class ExperimentError(ValueError):
    """An input does not satisfy the supported experiment contract."""


def experiment_schema() -> dict:
    return json.loads(files("openwave").joinpath("schemas/experiment-1.0.json").read_text())


def _check(value, rule: dict, path: str) -> None:
    # Intentionally implements only the keywords used by our bundled schema.
    # The schema itself remains consumable by standard JSON Schema validators.
    if "const" in rule and value != rule["const"]:
        raise ExperimentError(f"{path}: expected {rule['const']!r}")
    kind = rule.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            raise ExperimentError(f"{path}: expected object")
        missing = set(rule["required"]) - value.keys()
        extra = value.keys() - rule["properties"].keys()
        if missing:
            raise ExperimentError(f"{path}: missing properties {sorted(missing)}")
        if extra:
            raise ExperimentError(f"{path}: unknown properties {sorted(extra, key=str)}")
        for key, item in value.items():
            _check(item, rule["properties"][key], f"{path}.{key}")
    elif kind in ("number", "integer"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ExperimentError(f"{path}: expected {kind}")
        if isinstance(value, float) and not math.isfinite(value):
            raise ExperimentError(f"{path}: expected finite number")
        if kind == "integer" and value != int(value):
            raise ExperimentError(f"{path}: expected integer")
        if not rule["minimum"] <= value <= rule["maximum"]:
            raise ExperimentError(f"{path}: must be between {rule['minimum']} and {rule['maximum']}")


def validate_experiment(document: object) -> dict:
    """Return a defensive, normalized copy or raise ExperimentError.

    No solver construction, code evaluation, or filesystem output occurs here.
    """
    _check(document, experiment_schema(), "$")
    result = deepcopy(document)
    for key in ("nx", "ny"):
        result["mesh"][key] = int(result["mesh"][key])
    for key in ("modes", "seed"):
        result["solver"][key] = int(result["solver"][key])
    nx, ny = result["mesh"]["nx"], result["mesh"]["ny"]
    if nx * ny > 32768:
        raise ExperimentError("$.mesh: at most 32768 cells are supported")
    if result["solver"]["modes"] + 1 >= nx * ny:
        raise ExperimentError("$.solver.modes: must be at least two fewer than mesh cells")
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ExperimentError(f"Duplicate JSON property: {key}")
        result[key] = value
    return result


def load_experiment(path: str | Path) -> dict:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError) as exc:
        raise ExperimentError(f"Invalid experiment JSON: {exc}") from exc
    return validate_experiment(document)
