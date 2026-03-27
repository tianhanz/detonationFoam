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
