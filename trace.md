# detonationFoam - Learning & Documentation Trace

## Task
Create learning materials and reference documentation for the detonationFoam codebase, stored in `docs/` directory for long-term use.

## Changes
- `docs/README.md` — Index page linking all documentation
- `docs/learning-path.md` — 6-level progressive curriculum with checkpoints
- `docs/architecture.md` — Solver internals, algorithm flow, class map
- `docs/config-reference.md` — Every input file parameter explained
- `docs/simulation-cookbook.md` — Step-by-step workflows for common tasks
- `docs/troubleshooting.md` — Common errors, diagnosis, fixes

## Approach
1. Read all source files (main solver, equation files, flux schemes, DLBFoam, ROUNDSchemes, dynamicMesh2D)
2. Read all tutorial configuration files to verify parameter values
3. Tested compilation on available OpenFOAM 9 (partial compatibility documented)
4. Tested blockMesh + setFields on tutorial case (works on OF9)
5. Organized knowledge into progressive learning path + practical reference docs

### EARS — Progress (2026-03-27 17:48)
- **Completed**: Full OF8→OF9 port. All components compile and run on OpenFOAM 9.
- **Main solver port** (3 files): Header renames, library renames, `thermo.lookup` → `thermo.properties().lookup`, combustion model de-templating
- **DLBFoam port** (7 files): `StandardChemistryModel<ReactionThermo,ThermoType>` → `standardChemistryModel<ThermoType>`, `BasicChemistryModel<ReactionThermo>::correct()` → `basicChemistryModel::correct()`, `thermo.db()` → `thermo.T().mesh()` / `this->mesh()`, macro instantiation rewrite (`forCommonGases` → `forCoeffGases`, drop `forPolynomials`, drop ReactionThermo arg), added `OSspecific.H` for `mkDir`
- **Tested**: Tutorial case (1D NH3/O2 detonation) runs, shock propagates at 0.01m after 16 timesteps, p/T ranges correct
- **Warning**: `libODE_DLB.so` not built (DLBFoam ODE lib not in Allwmake) — benign, not needed for standard `ode` solver

### EARS — Progress (2026-03-27 23:01)
- **Completed**: Post-simulation visualization and verification report
- **New files**: `docs/verification-report.md` (comprehensive markdown report with 6 embedded figures), `docs/figures/` (6 PNG diagnostic plots)
- **Simulation insight**: Tutorial case initial conditions have TWO fronts — thermodynamic discontinuity at x=5mm (from setFields: 9.12 MPa driver) and species front at x=10mm (from 0/ directory: N₂→NH₃/O₂ transition). The velocity ramp (0→1700 m/s) represents a pre-developed blast expansion fan.
- **Key discovery**: Chemistry is extremely stiff — 33 species / 251 reactions with seulex ODE solver. Single-core throughput is ~1 ns per 5 min wall time. Full detonation development (1–10 μs) requires MPI parallel execution.
- **Verification checks passed**: Shock captured in 2–3 cells, no oscillations; EOS consistency (p/ρT = R_mix in all regions); species conservation; stable CFL-adaptive timestepping
- **Limitation**: 8 ns simulated — too short for chemistry to activate (NH₃/O₂ induction time ~ μs). Radicals and heat release are negligible. Need longer runs for ZND structure verification.

### EARS — Progress (2026-03-28 07:33)
- **Task**: Adapt ~/asurf Bohrium infrastructure for detonationFoam; design production detonation cases
- **Bohrium setup**: ACCESS_KEY and PROJECT_ID already configured in env. `bohr` CLI at ~/.bohrium/bohr. No pre-built OpenFOAM image on Bohrium (platform focuses on MD/DFT), but Docker Hub public images work: `microfluidica/openfoam:9` (420 MB, actively maintained) recommended as base.
- **Created**: `bohrium/submit_detonation.py` — adapted from asurf's batch_submit.py for OpenFOAM MPI jobs. Handles case staging, decomposeParDict patching, solver compilation on Bohrium, and result reconstruction.
- **Created**: `bohrium/chemkin2foam.py` — Chemkin-II → OpenFOAM .foam format converter. Needed because asurf mechanisms are Chemkin/YAML format but detonationFoam requires .foam dictionaries.
- **Decision**: Use Burke 2011 H2/O2 mechanism (10 species, 27 reactions) for production cases instead of extracting H2/O2 subset from NH3 mechanism. Burke 2011 is the gold standard for H2/O2 kinetics, well-validated for detonation.
- **Next**: Generate .foam mechanism files, create 1D H2/O2 CJ detonation and 2D cellular detonation case templates, test Bohrium submission.
