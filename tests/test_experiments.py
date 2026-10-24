"""Agent contract and integration regressions; runnable with unittest or pytest."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from openwave.experiment import ExperimentError, experiment_schema, load_experiment, validate_experiment
from openwave.runner import execute_experiment, run_experiment
from openwave.waveguide import RectangularWaveguide

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/wr90.json"


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.document = load_experiment(EXAMPLE)
        self.document["mesh"] = {"nx": 24, "ny": 12}

    def cli(self, *args):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), MPLBACKEND="Agg")
        env.pop("DISPLAY", None)
        return subprocess.run([sys.executable, "-m", "openwave", *map(str, args)],
                              cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)

    def test_example_and_defensive_copy(self):
        validated = validate_experiment(self.document)
        validated["geometry"]["width_mm"] = 99
        self.assertEqual(self.document["geometry"]["width_mm"], 22.86)
        self.assertEqual(experiment_schema()["properties"]["schema_version"]["const"], "1.0")

    def test_invalid_documents(self):
        invalid = [None, [], {}, True]
        for key, value in [("schema_version", "2.0"), ("kind", "arbitrary_python"),
                           ("geometry", []), ("mesh", {"nx": 256, "ny": 256})]:
            doc = deepcopy(self.document)
            doc[key] = value
            invalid.append(doc)
        for section, key, values in [
            ("geometry", "width_mm", [0, -1, True, "22", float("nan"), float("inf"), 10**400]),
            ("mesh", "nx", [3, 257, 4.5, False]),
            ("solver", "modes", [0, 13, "4", True]),
            ("solver", "seed", [-1, 2**32, 1.5, True]),
        ]:
            for value in values:
                doc = deepcopy(self.document)
                doc[section][key] = value
                invalid.append(doc)
        for section in [None, "geometry", "mesh", "solver"]:
            doc = deepcopy(self.document)
            (doc if section is None else doc[section])["typo"] = 1
            invalid.append(doc)
        for doc in invalid:
            with self.subTest(document=doc), self.assertRaises(ExperimentError):
                validate_experiment(doc)

    def test_missing_nested_setting(self):
        del self.document["solver"]["seed"]
        with self.assertRaisesRegex(ExperimentError, "seed"):
            validate_experiment(self.document)

    def test_standard_schema_agrees(self):
        # Optional cross-check; never a runtime dependency.
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema is unavailable")
        validator = Draft202012Validator(experiment_schema())
        validator.check_schema(experiment_schema())
        validator.validate(self.document)
        for value in [True, "24", 3, 4.5]:
            doc = deepcopy(self.document)
            doc["mesh"]["nx"] = value
            self.assertTrue(list(validator.iter_errors(doc)))

    def test_integral_json_numbers_normalized(self):
        self.document["mesh"]["nx"] = 24.0
        self.assertIsInstance(validate_experiment(self.document)["mesh"]["nx"], int)

    def test_malformed_duplicate_and_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            for contents in ['{', '{"kind":1,"kind":2}',
                             json.dumps(self.document).replace('22.86', 'NaN'), '\udcff']:
                path.write_bytes(contents.encode("utf-8", errors="surrogateescape"))
                with self.subTest(contents=contents), self.assertRaises(ExperimentError):
                    load_experiment(path)

    def test_validation_does_not_solve(self):
        with patch.object(RectangularWaveguide, "solve_te_modes", side_effect=AssertionError):
            validate_experiment(self.document)

    def test_numerical_result_matches_existing_solver_and_analytic(self):
        result = execute_experiment(self.document)
        guide = RectangularWaveguide(22.86e-3, 10.16e-3, 24, 12)
        legacy = guide.solve_te_modes(4)
        np.testing.assert_allclose([m["cutoff_frequency_hz"] for m in result.modes],
                                   [m.cutoff_frequency_hz for m in legacy], rtol=1e-10)
        self.assertLess(abs(result.modes[0]["cutoff_frequency_hz"] / guide.analytic_te_cutoff(1, 0) - 1), 0.005)
        self.assertEqual(result.fields.shape, (4, 12, 24))
        np.testing.assert_allclose(np.max(abs(result.fields), axis=(1, 2)), 1)

    def test_reproducible_bundle_and_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = (Path(tmp) / name for name in ("first", "second"))
            report = run_experiment(self.document, first)
            repeat = run_experiment(self.document, second)
            self.assertEqual(report, repeat)
            for artifact in first.iterdir():
                self.assertEqual(artifact.read_bytes(), (second / artifact.name).read_bytes())
            for name, info in report["artifacts"].items():
                self.assertEqual(info["sha256"], hashlib.sha256((first / name).read_bytes()).hexdigest())
            field = np.load(first / "fields.npy", allow_pickle=False)
            self.assertEqual(list(field.shape), report["field"]["shape"])
            np.testing.assert_allclose(np.load(first / "x_m.npy"), (np.arange(24) + 0.5) * 22.86e-3 / 24)
            self.assertEqual(json.loads((first / "results.json").read_text()), report)
            before = (first / "results.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run_experiment(self.document, first)
            self.assertEqual((first / "results.json").read_bytes(), before)

    def test_failed_solver_leaves_no_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "failed"
            with patch.object(RectangularWaveguide, "solve_te_modes", side_effect=RuntimeError("failed")):
                with self.assertRaises(RuntimeError):
                    run_experiment(self.document, target)
            self.assertFalse(target.exists())

    def test_nonfinite_solver_output_leaves_no_bundle(self):
        from openwave.waveguide import Mode
        bad_mode = Mode(1, 1.0, 1.0, np.full((12, 24), np.nan))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "failed"
            with patch.object(RectangularWaveguide, "solve_te_modes", return_value=[bad_mode]):
                with self.assertRaisesRegex(RuntimeError, "non-finite"):
                    run_experiment(self.document, target)
            self.assertFalse(target.exists())

    def test_cli_schema_validate_run_without_display(self):
        schema = self.cli("schema")
        self.assertEqual(schema.returncode, 0, schema.stderr)
        self.assertEqual(json.loads(schema.stdout), experiment_schema())
        valid = self.cli("validate", EXAMPLE)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)["status"], "valid")
        with tempfile.TemporaryDirectory() as tmp:
            result = self.cli("run", EXAMPLE, "--output", Path(tmp) / "run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "success")
            self.assertTrue((Path(tmp) / "run/results.json").is_file())

    def test_cli_errors_are_json_with_nonzero_exit(self):
        for args in [("validate", "/nonexistent/openwave.json"), ("validate",),
                     ("run", EXAMPLE), ("schema", "--typo"), ("unknown",)]:
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertEqual(json.loads(result.stderr)["status"], "error")

    def test_cli_solver_failure(self):
        from contextlib import redirect_stderr
        from io import StringIO
        from openwave.cli import main
        error = StringIO()
        with patch("openwave.runner.run_experiment", side_effect=RuntimeError("no convergence")):
            with redirect_stderr(error):
                self.assertEqual(main(["run", str(EXAMPLE), "--output", "unused"]), 1)
        self.assertEqual(json.loads(error.getvalue())["error"]["code"], "execution_failed")

    def test_cli_has_no_plotting_or_gui_import(self):
        code = "from openwave.cli import main; main(['schema']); import sys; assert 'matplotlib.pyplot' not in sys.modules; assert 'tkinter' not in sys.modules"
        result = subprocess.run([sys.executable, "-c", code], env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_cli_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mode.png"
            result = self.cli("--nx", "24", "--ny", "12", "--modes", "1", "--plot", path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("mode, cutoff_GHz", result.stdout)
            self.assertTrue(path.read_bytes().startswith(b"\x89PNG"))

    def test_gui_validation_remains_available(self):
        from openwave.gui import validate_inputs, cutoff_explanation
        self.assertEqual(validate_inputs("30", "12"), (30.0, 12.0, 4))
        for width in ["nan", "0", "bad"]:
            with self.assertRaises(ValueError):
                validate_inputs(width, "12")
        self.assertIn("cannot travel", cutoff_explanation(6.5e9))


if __name__ == "__main__":
    unittest.main()
