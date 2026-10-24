# Reddit feedback and improvement priorities for OpenWave

Research date: 2026-10-24. This is a synthesis of individual public Reddit discussions, **not** a representative user survey, commercial viability assessment, or full source-code audit.

## Executive conclusion

Open-source RF/EM tools address a real accessibility and workflow problem. However, RF practitioners are increasingly skeptical of polished AI-assisted simulators without reproducible numerical evidence. OpenWave's strongest near-term direction is **a narrowly scoped, trustworthy rectangular-waveguide TE teaching tool with a GUI and reproducible headless experiments**—not a general-purpose CST/HFSS substitute.

## Current repository baseline — already implemented or documented

Based on [README](../README.md), [architecture](ARCHITECTURE.md), [AI-agent workflow](AI_AGENT_WORKFLOW.md), and [MCP documentation](MCP_SERVER.md):

- Educational GUI for ideal perfectly conducting rectangular waveguides, cutoff frequencies, and relative longitudinal magnetic field (H_z) patterns.
- A cell-centred 2-D scalar finite-difference TE eigenproblem. The README **already states analytical cutoff and mesh-convergence tests exist**.
- Versioned JSON experiment schema, semantic validation, CLI execution, structured results, input/source hashes, and reproducibility provisions.
- Optional local stdio MCP server with schema/validate/run tools, bounded compute/output locations, and client tests.
- Documented limits: no TM, driven response, S-parameters, conductor loss, arbitrary CAD, or full 3-D EM.

The items above are **not missing features**. The recommendations below concern clearer external evidence, student usability, and future engineering governance.

## What Reddit discussions indicate

| Source | Observations (claims/opinions of commenters) | OpenWave implication |
| --- | --- | --- |
| [Fairbeam open-source antenna app](https://www.reddit.com/r/rfelectronics/comments/1x3cp6q/) | Enthusiasm for free tools coexisted with complaints about many AI-assisted RF apps and requests to disclose AI use. A validation caveat earned trust from another commenter. | State AI involvement honestly, and show independent calculations rather than relying on demos. |
| [RF PCBs used to validate a new solver](https://www.reddit.com/r/rfelectronics/comments/1v6kboy/) | Engineers requested analytical/reference comparisons, measured setup/calibration details, honest unfavorable results, and scrutiny of speed claims. | Publish numerical benchmarks with methods, tolerances, failures, and convergence. Measurements complement, but do not replace, controlled numerical checks. |
| [EM GUI around Palace](https://www.reddit.com/r/rfelectronics/comments/1s6z9ks/) | Requests included parametric changes, edit history, mesh view, and CAD exchange; participants disagreed on GUI versus code-defined geometry. | Serving both humans and scripts is sensible; do not take on full CAD complexity at the present teaching scope. |
| [Magnelio Python EM library](https://www.reddit.com/r/rfelectronics/comments/1vt0hfw/) | Developer foregrounded published numerical methods, validation, documentation, standard result workflows; some commenters offered to test it. | Evidence and interoperability matter; a Python interface is useful but not unique differentiation. |
| [WaveFEM update](https://www.reddit.com/r/rfelectronics/comments/1oaivfh/) | Describes a broader 3-D integrated workflow with meshing and claimed reference comparisons. | Avoid feature parity with general-purpose solvers before validating the narrow classroom workflow. |
| [Programmatic circuit simulation debate](https://www.reddit.com/r/rfelectronics/comments/1unhv11/) | Some wanted Python-first generation; others preferred schematic capture for ordinary circuit work. | Define the actual learner task; do not assume every student wants MCP. |
| [AI code and junior developers](https://www.reddit.com/r/ExperiencedDevs/comments/1po21hq/) | Several engineers criticized code authors who could not explain/debug generated implementations. Others supported bounded AI use and testing. | Maintainer must own physics, architecture, review, and repair—even when AI writes patches. |
| [Free RF solver recommendations](https://www.reddit.com/r/rfelectronics/comments/j18f2d/) | Free/open alternatives were valued, but immature workflows were criticized as burdensome. | Make first installation and experiment easy and reliable. |

These are anecdotal and sometimes conflicting observations, not consensus or proof of market demand.

## Prioritized backlog

### P0 — Publish a numerical validation dossier

**First inventory the existing analytical-cutoff and mesh-convergence tests.** Reuse them rather than recreating them. Produce a reproducible benchmark for several rectangular-guide dimensions and mesh sizes, including analytic TE cutoff references, error, convergence behavior, parameters, solver version, and commands. Explain field sign ambiguity and nearly degenerate modes; numerical eigenpair order does not imply a particular TE(m,n) label.

**Acceptance:** An independent reader can run the benchmark and regenerate a numeric table/plot; reference equations and errors are explicit; unfavorable cases and unsupported phenomena are documented. This is additional public evidence, not a claim that current tests are absent.

### P0 — Protect the teaching scope

Make the distinction among relative H_z sign, power, cutoff, propagation, and unsupported physical effects impossible to miss in the first experiment.

**Acceptance:** A new learner can explain what the mode plot means and name two quantities that cannot be inferred from it.

### P1 — Check equivalence across interfaces

Inventory existing parity tests first. Confirm that equivalent dimensions/mesh/mode inputs through GUI, legacy CLI, JSON runner, and local MCP lead to equivalent physical results with justified numerical tolerances. Preserve headless operation, resource guards, and output confinement. Exact pixel/byte identity is not generally required.

**Acceptance:** A documented cross-interface example reports matching cutoff values; GUI and MCP tests remain stable.

### P1 — State an AI-assisted engineering policy

If the repository does not already document it, disclose where AI assists (implementation, documentation, test scaffolding), while making the human maintainer accountable for equations, code review, numerical references, bugs, and limitations. Require independent expected results when solver logic changes. Keep patches reviewable.

**Acceptance:** Every numerical change has a derivation/reference, a clear test oracle, and a maintainer who can explain the implementation without an LLM.

### P1 — Observe 3–5 real students

Ask learners to install OpenWave from the README, change WR-90 dimensions, explain the result, and save/inspect output without coaching. Record failures, comprehension errors, installation time and environment. Fix the largest observed obstacles.

**Acceptance:** Publish a brief anonymized report and resolve the two most common blockers. A tiny study does not establish a market.

### P2 — Make evidence easy to find

Link validation results and a one-command reproducible example from README; consider a concise “suitable / unsuitable uses” table. Preserve schema versioning if artifacts change.

**Acceptance:** The first-time user can locate the benchmark, recreate it, and read the caveats without digging through source code.

## Defer for now

Do not expand to full CAD/3-D solvers, TM, lossy or driven simulation, S-parameters, or more AI tools solely because competing demos have them. Those additions need separate validation and demonstrated user demand. Do not make commercial-readiness or performance claims based on Reddit applause.

## Next externally reviewable artifact

A **WR-90 TE validation report** based on the existing tests and example: cutoff comparison table, mesh-convergence plot, reproducible command, reference equation, mode-convention explanation, and known limits. Then ask a specific technical-feedback question on r/rfelectronics, such as which further benchmark would increase confidence. Check subreddit rules first; no Reddit post has been submitted.

## Positioning and evidence limitations

Suggested positioning: *OpenWave is an open-source rectangular-waveguide TE learning environment combining a student-friendly GUI, bounded machine-readable experiments, and transparent numerical validation.*

These discussions suggest pain around licensing and workflow fragmentation; they do **not** establish willingness to pay, MCP demand, or broad market fit. Competitor feature/performance claims in posts were not independently verified. This review did not execute OpenWave tests or conduct actual user interviews.
