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

### EARS — Progress (2026-03-27 17:24)
- **Completed**: Learning docs created in `docs/`, pushed to `tianhanz/detonationFoam` branch `vk/8b8c-learn-code`
- **Git setup**: origin → tianhanz fork (SSH), upstream → JieSun-pku original. SSH key configured.
- **Key discovery**: OF8 not available in apt (removed from openfoam.org repo). OF9 installed but has breaking API changes.
- **Decision**: Port detonationFoam to OF9 instead of trying to install OF8. User confirmed DLBFoam must be included.
- **Current task**: Planning OF8→OF9 port. Research complete — identified all header renames, library changes, and the `StandardChemistryModel` de-templating needed for DLBFoam.
- **Risk**: DLBFoam port is non-trivial (chemistry model went from 2 template params to 1 in OF9). Main solver port is straightforward (~6 line changes + Make/options).
