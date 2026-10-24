# Architecture

OpenWave keeps its existing physics and student interface, with explicit seams:

| Layer | Modules | Responsibility |
| --- | --- | --- |
| Experiment contract | `experiment.py`, `schemas/experiment-1.0.json` | Version dispatch through schema constants, structural and semantic validation; no numerical/UI imports |
| Physics | `constants.py`, `grid.py`, `operators.py`, `waveguide.py` | Existing scalar TE finite-difference solver and numerical types |
| Application service | `runner.py` | Convert validated settings into solver inputs, normalize output sign, expose in-memory results |
| Artifacts | `runner.py` writer functions | Canonical JSON, NumPy arrays, hashes, provenance, staged publication |
| Agent/human CLI | `cli.py`, `__main__.py` | Argument parsing, JSON protocol, exit codes, legacy flags |
| Student GUI | `gui.py`, `plotting.py` | Existing desktop controls, explanatory text, rendering and image export |

Dependencies point inward: the CLI calls the runner, which calls validation and
physics. Physics never imports the CLI, runner, or GUI. The GUI continues to call
the same physics API directly. Plotting imports are lazy in the legacy CLI path;
agent commands never import plotting or Tkinter.

`execute_experiment` is the backend adapter boundary. Its `ExperimentResult`
contains the validated document, numeric mode summaries, `[mode,y,x]` fields,
and metre-valued coordinates. A later Rust extension or subprocess adapter can
implement that boundary without changing the experiment JSON or GUI. Preserve
numerical parity tests when replacing it. The only solver addition here is an
optional keyword-only seed controlling ARPACK's starting vector; calls without
it retain the historical behavior and signatures of positional arguments.

The longer-term numerical boundary is a discrete-complex layer supporting nodes,
edges, faces, cells, incidence matrices, and material-weighted Hodge operators.
That can enable Nédélec FEM without coupling the solver to one mesh generator.
It is future work, outside this milestone.

See [AI-agent workflow](AI_AGENT_WORKFLOW.md) for versioning, artifacts, limits,
and reproducibility guarantees.
