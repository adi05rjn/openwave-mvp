# Numerical validation dossier

This document addresses the two numerical P0 gates in issue #6: the
**numerical validation dossier** and **cross-interface physical consistency**.
It records what has been checked, how to regenerate every number, why the
observed error has the size it has, and what remains unchecked.

Scope: ideal PEC, vacuum-filled, rectangular waveguide; scalar TE eigenmodes
from OpenWave's cell-centred finite-difference solver. Nothing here says
anything about TM modes, losses, dielectric loading, other geometries, driven
problems or physical field amplitudes.

## Regenerate everything

```bash
python -m pip install -e '.[dev,mcp]'
python benchmarks/validation_dossier.py --output artifacts/validation
python -m pytest -q tests/test_validation.py tests/test_interfaces.py
xvfb-run -a python -m pytest -q tests/test_gui_session.py   # needs Tk + Xvfb
```

The script runs in a few seconds and writes `report.md` (every table below,
plus the full per-mode table), `results.json` and `convergence.png`. All runs
use ARPACK seed 0. The numbers below were produced with Python 3.13.18,
NumPy 2.5.4 and SciPy 1.18.1 from the physics modules at `56a6bb8` (this work
does not change `constants.py`, `grid.py`, `operators.py` or `waveguide.py`).
CI regenerates the dossier on every push.

## 1. The two reference solutions

Neither reference is computed by OpenWave's solver.

### Continuum TE modes

For an ideal PEC guide of width *a* and height *b*, the TE modes satisfy
∇ₜ²H_z + k_c²H_z = 0 with ∂H_z/∂n = 0 on the walls. Separation of variables
gives (Pozar, *Microwave Engineering*, 4th ed., §3.3):

    H_z ∝ cos(mπx/a) cos(nπy/b),   k_c² = (mπ/a)² + (nπ/b)²,   f_c = c₀ k_c / 2π

for integers m, n ≥ 0, not both zero.

### Exact eigenpairs of the discrete operator

OpenWave stores H_z at cell centres x_i = (i + ½)Δx, i = 0 … n_x − 1, and uses
the 1-D operator

    interior:  (u_{i−1} − 2u_i + u_{i+1}) / Δx²
    boundary:  (u_1 − u_0) / Δx²   and   (u_{n−2} − u_{n−1}) / Δx²

The boundary rows are the interior formula with a mirrored ghost value
u_{−1} = u_0 (zero normal difference across the wall face).

Try u_i = cos(θ(i + ½)) with θ = mπ/n_x. For an interior row,
cos(θ(i − ½)) + cos(θ(i + 3/2)) = 2 cos θ · cos(θ(i + ½)), so the row returns
−(4/Δx²) sin²(θ/2) · u_i. At i = 0 the ghost value cos(−θ/2) equals u_0, so the
boundary row gives the same result; at i = n_x − 1, cos(mπ + θ/2) equals
cos(mπ − θ/2), so it does too. The n_x vectors m = 0 … n_x − 1 are the
orthogonal DCT-II basis, so this is the complete spectrum. The 2-D operator is
a Kronecker sum, so its eigenpairs are products:

    λ_mn = (2/Δx · sin(mπ/2n_x))² + (2/Δy · sin(nπ/2n_y))²
    v_mn = cos(mπx/a) cos(nπy/b) sampled at the cell centres

So the discrete eigenvectors are **exactly** the continuum modes sampled at
the unknowns. Only the eigenvalues carry discretization error.

### Why the error has the size it has

With k = mπ/a and h = Δx, (2/h · sin(kh/2))² = k²(1 − (kh)²/12 + O(h⁴)).
Summing both directions and taking a square root, the relative cutoff error is

    f_c,h / f_c − 1 ≈ −(k_x⁴ Δx² + k_y⁴ Δy²) / (24 k_c²)

Consequences you can check in the tables:

- every computed cutoff is **below** the analytical value;
- the error is **second order**: halving the cell size divides it by 4;
- the error grows with mode order, roughly as (cells per half-wavelength)⁻².
  For WR-90 TE10 on the 61 × 31 example mesh it is
  −π²/(24 · 61²) = −1.11 × 10⁻⁴, which is exactly the observed
  6.556416 GHz against 6.557140 GHz.

## 2. Checks across geometries and higher-order modes

Eight modes were solved for five guides chosen to exercise different cases:
WR-90 (aspect 2.25), WR-90 rotated 90°, WR-28 (aspect exactly 2, so TE20 and
TE01 are degenerate), a square guide (TE10/TE01, TE20/TE02, TE12/TE21
degenerate) and a 20 × 10.05 mm guide whose TE01 and TE20 are 0.5 % apart.
Meshes keep Δx ≈ Δy. A sixth guide (30 × 5 mm, aspect 6) is in the tests.

For each solver mode the dossier reports:

| Check | What it isolates | Worst case observed |
| --- | --- | --- |
| Solver vs exact discrete eigenvalue | Eigensolver (ARPACK) error | 2.2 × 10⁻¹³ relative |
| Solver vs continuum cutoff | Discretization error | agrees with the formula above to within 0.04 % of its value in every row |
| ‖Av − λv‖ / λ‖v‖ | Eigenpair residual | 4.9 × 10⁻¹² |
| Max off-diagonal of the field Gram matrix | Orthogonality | 4.0 × 10⁻¹⁵ |
| Principal angle to the oracle eigenspace | Mode shape | sin θ ≤ 3.5 × 10⁻¹² |

WR-90 on a 90 × 40 mesh, as an example (full table for all guides in
`report.md`):

| Solver mode | Oracle label | Solver GHz | Analytic GHz | Rel. error | Predicted |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | TE10 | 6.556807 | 6.557140 | −5.08 × 10⁻⁵ | −5.08 × 10⁻⁵ |
| 2 | TE20 | 13.111618 | 13.114281 | −2.03 × 10⁻⁴ | −2.03 × 10⁻⁴ |
| 3 | TE01 | 14.749774 | 14.753566 | −2.57 × 10⁻⁴ | −2.57 × 10⁻⁴ |
| 4 | TE11 | 16.141486 | 16.145086 | −2.23 × 10⁻⁴ | −2.23 × 10⁻⁴ |
| 5 | TE30 | 19.662434 | 19.671421 | −4.57 × 10⁻⁴ | −4.57 × 10⁻⁴ |
| 6 | TE21 | 19.735003 | 19.739607 | −2.33 × 10⁻⁴ | −2.33 × 10⁻⁴ |
| 7 | TE31 | 24.579812 | 24.589276 | −3.85 × 10⁻⁴ | −3.85 × 10⁻⁴ |
| 8 | TE40 | 26.207261 | 26.228562 | −8.12 × 10⁻⁴ | −8.12 × 10⁻⁴ |

The oracle label is assigned by matching the exact discrete eigenvalue, not by
the solver's index. The rotated guide gives identical cutoffs with the labels
transposed.

**Boundary condition.** The Neumann condition is built into the operator rather
than checked afterwards: the mirrored-ghost rows impose a zero difference across
each wall face. Because the computed vectors equal sampled cos(mπx/a)cos(nπy/b)
to round-off (row "Mode shape" above), they inherit the continuum condition. A
one-sided difference between the first cell centre and the wall is O(Δx), not
zero, because there is no unknown on the wall; that is expected for a
cell-centred scheme and is not a residual of the eigenproblem.

## 3. Mesh convergence (WR-90)

| Mode | 18 × 8 | 36 × 16 | 72 × 32 | 144 × 64 | Observed order (last step) |
| --- | ---: | ---: | ---: | ---: | ---: |
| TE10 | −1.27 × 10⁻³ | −3.17 × 10⁻⁴ | −7.93 × 10⁻⁵ | −1.98 × 10⁻⁵ | 2.000 |
| TE20 | −5.07 × 10⁻³ | −1.27 × 10⁻³ | −3.17 × 10⁻⁴ | −7.93 × 10⁻⁵ | 2.000 |
| TE01 | −6.41 × 10⁻³ | −1.61 × 10⁻³ | −4.02 × 10⁻⁴ | −1.00 × 10⁻⁴ | 2.000 |
| TE11 | −5.56 × 10⁻³ | −1.39 × 10⁻³ | −3.48 × 10⁻⁴ | −8.71 × 10⁻⁵ | 2.000 |
| TE30 | −1.14 × 10⁻² | −2.85 × 10⁻³ | −7.14 × 10⁻⁴ | −1.78 × 10⁻⁴ | 2.000 |

Values are relative cutoff errors against the continuum formula. The figure
`convergence.png` plots the same data on log–log axes against a slope-2 line.

## 4. Ambiguities a user must know about

**Sign.** Eigenvectors are defined up to sign. The JSON bundle makes the first
sample with |H_z| > 0.5 positive; the GUI and legacy CLI do not normalize sign.
Red/blue in a plot is relative sign only.

**Indexing.** "Mode k" means the k-th smallest computed eigenvalue. It is not an
analytical TE(m,n) label. On the 20 × 10.05 mm guide the continuum order is
TE10, TE01 (14.915 GHz), TE20 (14.990 GHz). On an 80 × 40 mesh the solver keeps
that order. On a legal but anisotropic 10 × 20 mesh, TE20 is under-resolved
(5 cells per half-wavelength), drops to 14.744 GHz, and becomes solver mode 2.
A label can only be assigned by checking both the cutoff and the field.

**Degeneracy.** When two modes share a cutoff, any rotation within their
eigenspace is an equally valid answer. In the square guide all five seeds tested
give identical cutoffs and the same two-dimensional subspace
(sin θ ≤ 1.5 × 10⁻¹³), but the individual mode-1 field can change: on the
development machine its overlap with the seed-0 field ranged from 0.06 to 0.99,
while with numpy 1.26 / scipy 1.12 the smallest overlap over the same seeds was
0.93. How far a run rotates therefore depends on library versions. Rotating the
pair by any angle gives equally valid modes (checked in
`test_rotating_a_degenerate_pair_gives_equally_valid_modes`). Compare subspaces,
never individual fields, in a degenerate pair. The seed makes a run reproducible; it does not
make a degenerate field physically meaningful.

**Mode count can split a degenerate group.** WR-28 has TE02 and TE40 at the same
cutoff, as the 8th and 9th eigenvalues. Asking for 8 modes returns one vector
from that two-dimensional eigenspace, which is some unspecified mixture of TE02
and TE40 (it lies in the eigenspace to sin θ = 1.2 × 10⁻¹³, but matches neither
pure mode). If the last requested cutoff equals the next analytical cutoff,
request more modes before interpreting the last field.

## 5. Unfavorable cases

Under-resolution, WR-90 on a 12 × 6 mesh (the schema allows meshes down to
4 × 4):

| Mode | Cells per half-wavelength along x | Relative error |
| --- | ---: | ---: |
| TE10 | 12 | −2.85 × 10⁻³ |
| TE20 | 6 | −1.14 × 10⁻² |
| TE30 | 4 | −2.55 × 10⁻² |
| TE40 | 3 | −4.51 × 10⁻² |
| TE60 | 2 | −9.97 × 10⁻² |
| TE80 | 1.5 | −1.73 × 10⁻¹ |

The solver does not fail on coarse meshes; it returns confidently wrong
numbers. Errors stay predictable from the formula in §1, but at 4 or fewer
cells per half-wavelength they exceed 2 %. Near-degenerate pairs on
anisotropic meshes can swap order (§4). No non-convergent ARPACK case was found
in these runs; ARPACK convergence on larger meshes or with many more modes has
not been studied.

## 6. Cross-interface consistency

The same physical problem must give the same cutoffs through every entry point.
`tests/test_interfaces.py` solves WR-90 and a 30 × 12 mm guide on the GUI's
81 × 41 mesh through each interface and compares against the **exact discrete
oracle**, not against another interface:

| Interface | How it is exercised | Tolerance |
| --- | --- | --- |
| GUI computation (`gui.solve_for_display`) | in process; the same function the Update button calls | rtol 10⁻¹⁰ |
| JSON runner (`execute_experiment`) | in process, seed 0 | rtol 10⁻¹⁰ |
| `openwave run` | subprocess, reads `results.json` and `fields.npy` | rtol 10⁻¹⁰ |
| Legacy `openwave --width-mm …` | subprocess, parses printed text (6 decimals) | 10⁻⁶ GHz absolute |
| MCP `run_experiment` | real MCP client, bounded worker subprocess | rtol 10⁻¹⁰; fields equal to the runner's within 10⁻⁸ |
| Real GUI window | `tests/test_gui_session.py` under Xvfb; labels show 3 decimals | half a displayed digit (5 × 10⁻⁴ GHz) |

Fields from the GUI path and the JSON paths agree up to sign (overlap 1 to
10⁻⁹) for these non-degenerate modes.

Intentional differences, not drift:

| Interface | Default mesh | TE10 for WR-90 | Relative error |
| --- | --- | ---: | ---: |
| GUI (fixed, hidden from students) | 81 × 41 | 6.556729 GHz | −6.27 × 10⁻⁵ |
| Legacy CLI default | 81 × 41 | 6.556729 GHz | −6.27 × 10⁻⁵ |
| `examples/wr90.json` | 61 × 31 | 6.556416 GHz | −1.11 × 10⁻⁴ |

MCP additionally caps meshes at 4096 cells and 4 modes; the GUI always shows 4
modes. At the GUI's 3-decimal display, the 61 × 31 and 81 × 41 meshes are
visibly different (6.556 versus 6.557 GHz), so a student comparing the GUI
with the JSON example will see a last-digit difference. That is mesh, not a
bug.

**Real GUI session.** `tests/test_gui_session.py` opens the actual Tk window,
waits for the example to render, changes the width to 30 mm, presses Update,
selects pattern 3, saves a PNG, enters an invalid width (checks an error is
shown and the previous result kept) and presses Exit. Widgets are found by
walking the real window; only the native file dialog and error box are patched
because they would block on a person. On the development machine (cloud Linux
container, Python 3.12, Xvfb) Update took about 0.2 s and the whole session
about 1 s. The solve runs on the Tk event loop, but because the GUI mesh is
fixed the cost does not grow with the dimensions a student types. This has not
been measured on low-end student laptops.

## 7. What this dossier does not establish

- It has not yet been regenerated by an independent person, which is the
  issue's pass criterion for this gate.
- It validates the discrete scalar TE eigenproblem against its own continuum
  limit. It says nothing about TM modes, losses, materials, other shapes,
  driven response, or absolute field amplitudes.
- The physics module accepts `eps_r` and `mu_r`, but the 1.0 experiment schema
  is vacuum-only, and material scaling is not covered here.
- The GUI session was checked on Linux under Xvfb only, not on Windows, macOS
  or a real student desktop. The independent student usability gate in issue #6
  is untouched.
