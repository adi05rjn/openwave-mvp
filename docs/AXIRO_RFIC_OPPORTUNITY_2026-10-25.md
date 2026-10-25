# Axiro Semiconductor: RFIC electromagnetic verification opportunity

Research date: 2026-10-25  
Status: **discovery candidate; not an Axiro requirement, partnership, or product commitment**

## Executive decision

Investigate a **reproducible RFIC passive electromagnetic verification workbench**: take layout/stackup and solver outputs, extract RF metrics, compare with analytical or measured references, and produce auditable regression reports. The long-term reference category is Ansys HFSS/ADS Momentum/EMX, **not a claim of feature equivalence**.

The initial differentiator should be **cross-run, cross-solver, and measurement-versus-simulation validation**, rather than another bare EM solver, S-parameter plotter, or generic 3-D CAD GUI.

This is a possible *future* OpenWave research track. It does **not** replace the current rectangular-waveguide TE teaching scope or outrank the validation work in [Reddit feedback](REDDIT_FEEDBACK_2026-10-24.md).

## What the evidence actually says

| Evidence | Observation | Reasonable inference | What remains unknown |
| --- | --- | --- | --- |
| Axiro CEO interview (June 2026) | Cadence is central to IC development; HFSS is used for EM/finite-element analysis; Mentor/Synopsys also feature in the design flow. | Full-wave EM analysis matters to some Axiro engineering workflows. | Whether their bottleneck is accuracy, cost, runtime, automation, or data management. |
| Axiro RF engineer listing | Mentions RFIC layout and EM simulation with ADS Momentum, EMX, HFSS. | On-chip RF passives and layout parasitics are relevant to recruiting requirements. | How any team actually organizes simulations and regression checks. |
| Axiro product portfolio | RF/mmWave amplifiers, mixers, attenuators, switches, beamformers, and GaN PA modules. | RF loss, impedance, coupling, matching, and linearity are important product-level considerations. | Which component or frequency range offers a useful public benchmark. |

**Do not claim:** Axiro wants to replace HFSS; Axiro has validated this idea; Axiro would use, fund, buy, or contribute to the project. Those claims require direct interviews and evidence.

## Narrow problem statement

RFIC engineers need to answer repeatable, reviewable questions about a passive structure:

- Given a documented GDSII layout, layer stack, excitation/port setup, and frequency band, what S-parameters does a supported EM solver predict?
- For a spiral inductor, what are the *appropriately defined* equivalent inductance, series loss, Q, and self-resonance? Specify termination/reference-plane and frequency range.
- Does a geometry change improve the relevant metric without causing a mismatch, convergence failure, or runtime explosion?
- Do two solver runs (or simulation and measurement) agree within justified tolerances?
- Can another engineer regenerate the result with the same versions, settings, and input hashes?

Candidate input: Touchstone .s1p/.s2p results plus JSON metadata first; GDSII and an open process-stack configuration later. Candidate output: numeric metrics, frequency plots, per-band error summaries, pass/fail assertions, solver/mesh provenance, and a shareable report.

## Existing projects and why not duplicate them

| Project | Relevant capability | Positioning for this project |
| --- | --- | --- |
| [openEMS](https://www.openems.de/) | Open FDTD EM solver; Python scripting; port/S-parameter flow. | Reuse as a numerical backend, not rewrite as a first step. |
| [OpenParEM](https://github.com/OpenParEM/OpenParEM) | Open frequency-domain 2-D/3-D FEM for waveguides, ports, S-parameters, fields. | Evaluate as an independent comparison option. |
| [AWS Palace / IHP EM flow](https://ihp-open-pdk-docs.readthedocs.io/en/latest/em_simulation/em_simulation_overview.html) | FEM workflow and IHP SG13G2 process-stack integration. | Compare suitability to FDTD for small on-chip structures. |
| [EMStudio](https://github.com/IHP-GmbH/EMStudio) | GUI for EM workflows, script editing, geometry/port setup. | Do not clone its GUI without a validated user gap. |
| [gds2openEMS](https://github.com/VolkerMuehlhaus/gds2openEMS) | Existing IHP GDSII-to-openEMS workflow with stackup and S-parameter examples. | Integrate/reuse with license checks; avoid duplicate import code. |
| [scikit-rf](https://scikit-rf.readthedocs.io/) | Touchstone/network processing, transforms, Smith plots, comparisons. | Use as an analysis dependency. |
| [IHP Open PDK](https://github.com/IHP-GmbH/IHP-Open-PDK) | Public 130-nm SiGe BiCMOS RF process data and examples. | Use public, permitted examples only; open release is not a blanket production sign-off PDK. |

The IHP ecosystem already demonstrates GDSII-to-EM-to-Touchstone workflows. Therefore a plain *GDS import + plot S21* demo is **not novel enough**. Candidate differentiation is deterministic, automated verification; this must still be validated against existing tools.

## Relation to OpenWave today

As documented in [README](../README.md) and [architecture](ARCHITECTURE.md), OpenWave currently solves a **2-D scalar TE eigenmode problem** for ideal PEC rectangular waveguides. It presents cutoff frequencies and relative H_z patterns. It does **not** solve driven 3-D Maxwell problems, produce S-parameters, model on-chip process losses, or import arbitrary GDSII.

No current mode shape should be reinterpreted as a driven RFIC response. A future optional RF verification module should remain separate from the existing educational solver and preserve its CLI, GUI, JSON schema, MCP behavior, and tests. Prefer a post-processing and solver-adapter boundary before any attempt at native full-wave numerical methods.

The existing [Reddit feedback](REDDIT_FEEDBACK_2026-10-24.md) puts a WR-90 numerical validation dossier ahead of scope expansion. Complete and publish that gate first.

## Proposed user validation (no outreach conducted)

Interview **two or three working RFIC/EM engineers** using public, non-confidential examples:

1. Which RF passive structures do you simulate most often, and what takes the most manual effort?
2. What happens between GDS/layout, solver setup, Touchstone export, and circuit simulation?
3. How do you check mesh convergence, port/de-embedding assumptions, and reference impedance?
4. How do you compare revisions/corners and detect regressions today?
5. Would an offline CLI that emits an auditable S-parameter comparison report save time? What must be in it?
6. What would make the tool categorically unusable (accuracy, PDK restrictions, security, integration, runtime)?

**Decision gate:** continue beyond a small demonstration only if a concrete repeated pain point is confirmed and a public benchmark can independently validate the workflow. Do not solicit proprietary layouts, PDKs, models, measurements, or customer data.

## Risks and non-goals

- **Accuracy:** near-field/port conventions, calibration/de-embedding, mesh convergence, boundary conditions, materials, and losses can dominate apparent agreement.
- **Compatibility:** check license terms (especially GPL dependencies) before vendoring or redistribution; subprocess and independent adapters may be preferable.
- **Compute:** cap frequency points, sweeps, memory, wall time, and output volume; log versions and environment.
- **Claims:** no production sign-off, tape-out assurance, foundry qualification, mmWave accuracy, or HFSS equivalence without independent evidence.
- **Scope:** not a new 3-D FEM solver, commercial HFSS clone, full CAD front end, active transistor/noise/linearity simulator, or generalized multiphysics platform.

## Follow-on plan

See [RFIC verification implementation plan](RFIC_VERIFICATION_ROADMAP.md). It is **sequential and gated**: first finish OpenWave's existing validation priority; then build one small Touchstone comparison artifact; expand only when test evidence supports the next step.

## Sources

1. [Axiro CEO interview, Electronics For You, 2026-06-02](https://www.electronicsforu.com/technology-trends/we-are-not-a-startup-but-we-still-move-like-one-dr-naveen-yanduru-axiro-semiconductor)
2. [Axiro RF Design Engineer job listing](https://www.axiro.com/en/job-details/rf-design-engineer-turkey-1)
3. [Axiro RF product portfolio](https://www.axiro.com/en/products)
4. [Ansys HFSS product](https://ansys.synopsys.com/products/electronics/ansys-hfss)
5. [openEMS S-parameter/Touchstone documentation](https://docs.openems.de/en/stable/postproc/sparams.html)
6. [IHP OpenPDK EM simulation overview](https://ihp-open-pdk-docs.readthedocs.io/en/latest/em_simulation/em_simulation_overview.html)
7. [IHP EMStudio](https://github.com/IHP-GmbH/EMStudio)
8. [gds2openEMS workflow](https://github.com/VolkerMuehlhaus/gds2openEMS)
9. [scikit-rf documentation](https://scikit-rf.readthedocs.io/)

All company-specific demand statements above are either sourced observations or explicitly labeled inferences. No Axiro engineer was contacted during this research.
