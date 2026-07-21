# OpenWave MVP

OpenWave is a research-oriented RF/microwave computational electromagnetics prototype inspired by the workflow of commercial 3-D field solvers. This MVP deliberately starts with a narrow, verifiable problem: **TE eigenmodes of a PEC rectangular waveguide**.

## Implemented

- Structured 2-D cross-section grid
- Sparse Neumann Laplacian assembly
- TE scalar eigenmode solution
- Cutoff-frequency extraction
- Analytic rectangular-waveguide validation
- Propagation-constant calculation
- Field plotting
- CLI, example, and tests

## Scope limitation

This is not yet a full HFSS replacement. It currently uses a scalar finite-difference eigenproblem rather than full-vector tetrahedral finite elements with Nédélec edge basis functions. The architecture is intended to evolve toward that solver.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Run

```bash
openwave --width-mm 22.86 --height-mm 10.16 --modes 4
pytest
```

For WR-90, the analytic TE10 cutoff is approximately 6.557 GHz. The numerical result should converge toward it as the grid is refined.

## MVP-to-research roadmap

1. Replace scalar finite differences with triangular first-order FEM.
2. Implement Nédélec edge elements for the vector curl-curl equation.
3. Add Gmsh mesh import and physical-region tagging.
4. Add wave-port eigenproblems and modal normalization.
5. Implement driven frequency-domain solves and S-parameter extraction.
6. Add first-order absorbing boundaries and PML.
7. Add adaptive residual/error-based mesh refinement.
8. Add lossy, anisotropic, and dispersive materials.
9. Introduce PETSc/MPI and optional GPU backends.
10. Build Python CAD/setup APIs and a lightweight GUI.

## Proposed repository layout

```text
src/openwave/       solver package
tests/              numerical regression tests
examples/           executable models
docs/               architecture and mathematics
.github/workflows/  CI
```

## License

Apache-2.0. Commercial names are used only to describe the category of software and are not affiliated with this project.
