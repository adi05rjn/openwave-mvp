# Contributing to OpenWave

Thanks for considering a contribution. OpenWave is an educational solver for ideal, perfectly conducting rectangular waveguides. It currently solves a 2-D scalar finite-difference TE eigenproblem; contributions should preserve that documented scope unless the maintainer has agreed to a broader design.

## Before you start

1. Read [the README](README.md) to understand the supported workflows and limitations.
2. Read [the architecture notes](docs/ARCHITECTURE.md) before changing module boundaries.
3. Read [the validation dossier](docs/VALIDATION.md) before changing numerical code.
4. For experiment formats or agent-facing behavior, also read the [AI-agent workflow](docs/AI_AGENT_WORKFLOW.md) and [MCP server guide](docs/MCP_SERVER.md).

If you are unsure whether a change belongs in the project, open an issue to discuss the problem and proposed approach first.

## Set up a development environment

OpenWave requires Python 3.10 or newer. From a fresh clone:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,mcp]"
```

The optional MCP dependency is available on Python 3.11 and newer. The desktop GUI also requires Tkinter; Linux users may need to install the matching system package (for example, `python3-tk` on Ubuntu/Debian).

## Run checks before opening a pull request

Run the complete test suite:

```bash
python -m pytest -q
```

Run the repository's CI lint check:

```bash
ruff check --isolated --select E9,F .
```

For changes that affect numerical results, regenerate and inspect the validation dossier:

```bash
python benchmarks/validation_dossier.py --output artifacts/validation
```

The CI workflow also checks the supported Python versions and operating systems, the oldest declared numerical dependencies, the real desktop GUI under a virtual display, and the documented WR-90 and headless experiment workflows. A local run of the test suite does not replace those CI checks.

## Keep changes reviewable

- Prefer a focused change that solves one clearly stated problem.
- Avoid adding runtime dependencies unless there is a strong reason.
- Keep the physics layer independent of the CLI, runner, and GUI.
- Preserve experiment schema version `1.0`; incompatible contract changes need a new schema version.
- Preserve the CLI JSON protocol, documented exit codes, existing GUI controls, and MCP tool behavior unless the change explicitly requires otherwise.
- Do not commit generated artifacts, virtual environments, caches, or local machine configuration.
- Update documentation and tests when behavior or supported usage changes.

### Changes to numerical or physical behavior

Changes to the eigenproblem, boundary conditions, normalization, mode ordering, or solver require extra care:

- Explain the mathematical or physical basis and cite a suitable reference.
- Add an independent expected result to the tests; do not use the implementation's own output as its test oracle.
- Check analytical agreement and mesh convergence where relevant.
- Account for degeneracy by comparing eigenspaces rather than assuming individual eigenvectors are unique.
- State clearly what has and has not been validated.

Do not describe OpenWave as supporting TM modes, driven simulations, S-parameters, losses, arbitrary CAD geometry, full 3-D fields, or power calculations. Those are outside its current scope.

## Pull request checklist

Before requesting review, make sure your pull request:

- [ ] Explains the user problem and why the change is needed.
- [ ] Describes the implementation and any trade-offs.
- [ ] Includes or updates tests for changed behavior.
- [ ] Lists the checks you ran and their results.
- [ ] Updates relevant documentation.
- [ ] Calls out limitations, assumptions, and follow-up work.
- [ ] Discloses AI assistance when AI tools helped draft or implement the change.

Keep the pull request small enough to review as a coherent unit. The maintainer owns the physics and should be able to explain and verify any numerical change independently.

## Reporting a bug or proposing a feature

When reporting a bug, include the OpenWave version or commit, Python and dependency versions, the exact command or GUI steps, the input experiment (if shareable), the observed result, and the expected result. Remove private or sensitive data before posting.

For feature proposals, describe the user problem first, then the smallest useful behavior that would solve it. Please discuss major scope expansions before implementing them.
