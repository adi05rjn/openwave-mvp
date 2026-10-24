# AI-agent workflow

The desktop interface (`openwave-gui`) remains the student entry point. Agents can
create and execute declarative experiments without clicking the GUI, opening a
display, importing plotting code, or installing an LLM SDK. No model, provider,
API key, or network connection is required to run an experiment.

## Install and run

From an installed checkout (`python -m pip install -e .`):

```bash
openwave schema > experiment-schema.json
openwave validate examples/wr90.json
openwave run examples/wr90.json --output artifacts/wr90-agent
```

`python -m openwave` is equivalent to `openwave`. From an uninstalled checkout,
prefix it with `PYTHONPATH=src`. The example gives a first cutoff near 6.556 GHz
(the analytical TE10 value is about 6.557 GHz).

An agent should read `schema`, create a JSON document matching it, run `validate`,
fix any errors, and then run it into a **new** output directory. For a sweep,
create separate JSON inputs and output directories for each geometry or mesh.
Experiment documents contain data, never Python expressions or executable code.

Example prompt for an agent:

> Read `openwave schema` and `examples/wr90.json`. Create an experiment with a
> 30 mm by 10.16 mm vacuum-filled rectangular guide, keeping the example mesh,
> mode count, and seed. Validate it, run it into a new directory, and report the
> first cutoff frequency in GHz from `results.json`. State the mesh and solver
> assumptions. Do not infer S-parameters or losses from this TE eigenmode result.

## Experiment contract 1.0

See [the packaged JSON Schema](../src/openwave/schemas/experiment-1.0.json) and
[working WR-90 input](../examples/wr90.json). Every setting is explicit:

- `schema_version`: exactly `"1.0"`; unsupported versions fail validation.
- `kind`: exactly `"rectangular_waveguide_te"` (vacuum, ideal PEC boundaries).
- `geometry`: `width_mm` and `height_mm`, in millimetres, each 0.001–1,000,000.
- `mesh`: integer `nx` and `ny`, each 4–256, on the existing cell-centred grid.
- `solver`: `modes` from 1–12 and `seed` from 0–4,294,967,295.

Unknown properties, duplicate JSON keys, missing settings, booleans used as
numbers, non-finite numbers, and fractional integers are rejected. Integral JSON
numbers such as `24.0` are normalized to integers. Validation also enforces a
maximum of 32,768 cells and at least two more cells than requested modes. These
cross-field rules supplement JSON Schema and require `openwave validate` even
when an external schema validator passes. Limits bound student-sized jobs; they
are not a guarantee of convergence, accuracy, runtime, or suitability for hostile
multi-tenant execution.

The application checks the bundled schema's used keywords without adding a JSON
Schema runtime dependency. Future schema keywords must be implemented and tested
in the validator before being added. Future incompatible experiment formats must
use a new version; do not silently reinterpret old documents.

## CLI protocol

For agent commands, successful stdout is one JSON object. Errors go to stderr as
`{"status":"error","error":{"code":"...","message":"..."}}`, with empty stdout.
No progress text is mixed into those JSON streams. `--help` is human-readable.

| Exit | Meaning |
| --- | --- |
| 0 | Schema emitted, validation passed, or execution succeeded |
| 2 | Invalid experiment/arguments (`invalid_input`) or filesystem failure (`io_error`) |
| 1 | Solver/numerical execution failed (`execution_failed`) |

The historical flag-only command remains available and still prints its cutoff
table and saves a PNG. `openwave-gui` retains its existing controls and behavior.

## Output bundle

`run` refuses existing destinations. It stages the complete result beside the
destination and publishes it only after solving and writing succeed. A failed
solve does not leave a success report or partial bundle. Output paths are supplied
by the caller, never taken from experiment JSON.

| File | Contents |
| --- | --- |
| `experiment.json` | Validated input, canonical sorted JSON, UTF-8 with trailing newline |
| `results.json` | Result version, status, input digest, cutoff values in Hz and rad/m, field conventions, provenance, artifact sizes and SHA-256 hashes |
| `fields.npy` | Relative longitudinal magnetic field, float array indexed `[mode, y, x]` |
| `x_m.npy`, `y_m.npy` | Cell-centre coordinates in metres |

Read arrays with `numpy.load(path, allow_pickle=False)`. Field amplitude is
normalized to maximum absolute value 1, and the first sample with magnitude over
0.5 is made positive to resolve eigenvector sign ambiguity. Mode indices are
one-based sorted eigenpair indices, **not** inferred analytical TE(m,n) labels.
`results.json` lists the other artifacts; it does not hash itself. The result
report printed by `run` equals the report saved in the bundle.

Re-run `experiment.json` with the same software environment for comparison.
The seed fixes ARPACK's starting vector without changing NumPy's global random
state. The report records Python, OpenWave, NumPy and SciPy versions plus source
hashes of the solver modules and runner. No timestamps or absolute output paths
are embedded. Repeated runs in the tested environment produce identical bundle
bytes. Across platforms, BLAS libraries, CPUs, or dependency versions, compare
frequencies/fields with numerical tolerances; bit-for-bit identity is not
promised. Degenerate modes can rotate within their eigenspace, so compare their
subspaces rather than individual fields. Seeded execution is reproducibility
support, not a mesh-convergence or physical-accuracy certificate.

## Python API and backend boundary

```python
from openwave.experiment import load_experiment, validate_experiment
from openwave.runner import execute_experiment, run_experiment

experiment = load_experiment("examples/wr90.json")
result = execute_experiment(experiment)  # in-memory fields, coordinates, summaries
report = run_experiment(experiment, "artifacts/wr90-api")
```

`execute_experiment` validates again before constructing the solver. Validation,
solver execution, serialization, and UI concerns have separate modules. A future
Rust backend can replace the solver call inside the runner while retaining the
JSON contract and array/result conventions. There is no Rust rewrite in this
milestone.

## Tests

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

The agent integration tests can also run with the standard library test runner:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p test_experiments.py -v
```

Tests cover malformed inputs, the packaged schema, error streams/exit codes,
no-display execution, solver parity, analytical cutoff, reproducible bundles and
checksums, failed output publication, the existing CLI PNG, and GUI validation.
An optional cross-check uses `jsonschema` when already installed; it is not a
required dependency. Existing numerical and GUI tests remain in the pytest suite.
