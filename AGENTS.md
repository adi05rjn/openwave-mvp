# AGENTS.md

Guidance for AI assistants (coding agents and chat models) helping a student
or contributor use or change OpenWave. Read this before answering physics
questions or editing code. The README and `docs/` are the authoritative
sources; this file summarizes them and adds guardrails.

## What OpenWave is

OpenWave is an educational tool for **ideal, perfectly conducting rectangular
waveguides**. It solves a **2-D scalar finite-difference TE eigenproblem** and
reports:

- cutoff frequencies for the first TE modes, and
- the **relative** longitudinal magnetic field `H_z` for each mode.

It is not a driven full-wave simulator and not a substitute for commercial RF
or EM design tools.

## What it does not do

Do not claim, estimate, or imply any of the following from OpenWave output:

- TM modes, or any mode other than the scalar TE modes it computes
- driven simulations, sources, or excitation
- S-parameters, impedance, matching, or insertion loss
- conductor, dielectric, or other losses
- arbitrary CAD geometry, or anything other than a rectangle
- full 3-D electromagnetic fields
- physical accuracy beyond the documented analytical and mesh-convergence tests
- power flow, or the power carried by a mode

If a student asks about any of these, say the tool does not compute it and
explain the relevant physics in general terms, clearly labelled as general
knowledge rather than solver output.

## Conventions students routinely get wrong

- **H_z colors show relative sign, not magnitude, power, or heat.** Red and
  blue are opposite signs. The field is normalized to maximum absolute value 1.
- **Mode indices are sorted eigenpair order, not analytical TE(m,n) labels.**
  Do not map a solver mode to TE(m,n) unless the field and cutoff match that
  mode, and say so when you do.
- **Eigenvector sign is arbitrary.** The bundle fixes it by making the first
  sample with magnitude over 0.5 positive. Do not present signs as physical.
- **Cutoff is not propagation at a given frequency.** A mode propagates only
  above its cutoff. Below cutoff it does not propagate along the guide.
- **Degenerate modes can rotate within their eigenspace.** Compare subspaces,
  not individual fields, when two modes share a cutoff.
- **Mesh and seed are not accuracy guarantees.** Seeds fix the starting vector
  for reproducibility only. Check convergence under mesh refinement before
  trusting a number.

## Worked reference: WR-90

The bundled example is `examples/wr90.json` (22.86 mm by 10.16 mm, vacuum).
The first cutoff is about **6.556 GHz**, against an analytical TE10 value of
about **6.557 GHz**. Use these values as a check when a student runs the
example. If a result differs by more than the tolerance in the tests, the
result is suspicious, not the reference.

## Commands

Run these instead of guessing outputs:

```bash
openwave schema > experiment-schema.json
openwave validate examples/wr90.json
openwave run examples/wr90.json --output artifacts/wr90-agent   # new directory only
python -m pytest -q
```

Run `openwave validate` before `run`. `run` refuses existing output
directories, so pick a new one for each experiment. Successful agent-facing
commands print one JSON object to stdout. Errors go to stderr as JSON with empty
stdout. Exit codes: `0` success, `2` invalid input or filesystem error, `1`
solver failure.

## Teaching guidance

When helping a student:

- Ask for the prediction before the result. "What cutoff do you expect for
  WR-90, and why?" comes before the solver output.
- Verify AI-generated explanations against the solver and the analytical
  formula. Do not present a plausible explanation as checked when it has not
  been run.
- Say when you are unsure, and say what would resolve it (a run, a reference,
  a textbook section).
- Prefer the student's own wording of a result to a polished paragraph they
  cannot reproduce.
- Do not write the student's submission, solve their graded problem, or present
  solver output as a textbook result without the assumptions that produced it.

## Contributor guidance

- **The maintainer owns the physics.** Any change to the solver, eigenproblem,
  boundary conditions, normalization, or mode ordering needs a derivation or
  published reference and an independent expected result in the tests. Do not
  replace a test oracle with a snapshot of the code's own output.
- **Keep the layers separate.** Physics (`constants.py`, `grid.py`,
  `operators.py`, `waveguide.py`) must not import the CLI, runner, or GUI.
  Validation lives in `experiment.py`. See `docs/ARCHITECTURE.md`.
- **Preserve the contracts.** Do not change the experiment schema version
  `1.0` in place. Incompatible changes need a new version. Keep the CLI JSON
  protocol, exit codes, the GUI's existing controls, and the MCP tool behavior
  unchanged unless the change is explicitly requested.
- **Keep patches small and reviewable.** Do not add dependencies lightly. The
  runtime dependencies are NumPy, SciPy, and Matplotlib.
- **Run the tests.** `python -m pytest -q` must pass before a change is
  proposed. Say which tests you ran and which you could not.
- **Do not overclaim.** Do not describe a change as validated, accurate, or
  convergent without the evidence. Reddit feedback and roadmap documents in
  `docs/` are planning material, not evidence.
- **Do not add scope from competitor demos.** TM modes, S-parameters, losses,
  and RFIC verification are deferred. See `docs/REDDIT_FEEDBACK_2026-10-24.md`
  and `docs/RFIC_VERIFICATION_ROADMAP.md`.
- **State AI involvement.** If a change was drafted with AI assistance, say so
  in the pull request, and make sure the maintainer can explain the physics and
  the implementation without the assistant.

## Source of truth

- `README.md`: install, first experiment, current limits
- `docs/ARCHITECTURE.md`: module boundaries and backend seam
- `docs/AI_AGENT_WORKFLOW.md`: experiment contract, output bundle, reproducibility
- `docs/MCP_SERVER.md`: local MCP server and its safety limits
- `src/openwave/schemas/experiment-1.0.json`: the packaged JSON Schema

If this file disagrees with those documents, the documents win. Tell the user
about the disagreement rather than resolving it silently.
