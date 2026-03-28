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

### EARS — Progress (2026-03-28 08:59)
- **Local validation**: blockMesh + setFields succeed for 1D H2/O2 case (40K cells). Solver launch revealed format mismatches in generated .foam files.
- **PROBLEM**: `chemkin2foam.py` output didn't match detonationFoam's expected format:
  1. `species.foam` needs `species` keyword prefix (not just count + list)
  2. `thermo.foam` needs bare species blocks (no outer count/parens), `nMoles 1;`, inline `lowCpCoeffs(...)`, and **polynomial transport coefficients** (`muCoeffs<8>`, `muLogCoeffs<8>`, `kappaCoeffs<8>`, `kappaLogCoeffs<8>`)
  3. `reactions.foam` needs `reactions { ... }` wrapper (not count + parens)
- **ROOT CAUSE**: The tutorial's .foam format is detonationFoam-specific, not standard OpenFOAM dictionary format. Transport requires Chapman-Enskog polynomial fits derived from Lennard-Jones parameters.
- **FIX in progress**: Rewriting converter output routines to match exact tutorial format. Adding `compute_transport_polys()` using Neufeld (1972) collision integrals + numpy polynomial fitting.
- **Decision**: Using Euler (inviscid) solver type for 1D case — transport polynomials affect viscous terms only. But must still be valid for the thermo reader to parse.

### EARS — Progress (2026-03-28 10:12)
- **Bohrium submission fixed**: Root cause of earlier "服务内部错误" was using Docker Hub image (`microfluidica/openfoam:9`). Bohrium only supports images from `registry.dp.tech/`. Switched to `registry.dp.tech/dptech/ubuntu:20.04-py3.10` base image with OpenFOAM 9 installed via APT at runtime.
- **First submit attempt (Jobs 22319911, 22319913)**: Both submitted OK but failed with exit code 2. Root cause: `apt-key add` fails in the container because `gpg-agent` is not installed in the base image. `set -e` propagates the error.
- **Fix**: Changed GPG key import to `wget -qO /etc/apt/trusted.gpg.d/openfoam.asc` (no gpg-agent needed). Also installing `gnupg2` explicitly. About to resubmit both jobs.
- **Key learning**: Bohrium `image_address` must use `registry.dp.tech/dptech/...` format. All asurf jobs use this pattern. The SKILL.md at `~/asurf/.claude/skills/bohrium-job/SKILL.md` is the definitive reference for Bohrium job config.

### EARS — Stuck (2026-03-28 10:24)
- Context: Submitting detonationFoam cases to Bohrium cloud compute
- Goal: Get 1D and 2D H2/O2 detonation cases running on Bohrium
- Obstacle: Bohrium containers in China cannot reliably reach SourceForge (openfoam.org APT mirror). Three submission attempts failed:
  1. `microfluidica/openfoam:9` Docker Hub image → "服务内部错误" (Bohrium only supports `registry.dp.tech/` images)
  2. `registry.dp.tech/dptech/ubuntu:20.04-py3.10` + `apt-key add` → exit code 2 (no gpg-agent in container)
  3. Same image + `wget -qO /etc/apt/trusted.gpg.d/` fix → GPG works but `apt-get install openfoam9` times out connecting to SourceForge
- Tried: Three different run.sh approaches. Now switching to **portable binary approach**: package pre-compiled OF9 binaries + shared libs from local machine, ship them in the input directory, only install OpenMPI from Ubuntu repos (fast, reliable). This is the 4th edit to submit_detonation.py — should be the last, as it eliminates the SourceForge dependency entirely.

### EARS — Stuck (2026-03-28 10:48)
- Context: Still trying to get detonationFoam running on Bohrium
- Goal: Get solver running end-to-end on Bohrium cloud
- Obstacle: Two more approaches tried and failed since last note:
  4. **Portable binaries** (pre-compiled locally, shipped as files): GLIBC_2.34/2.35 mismatch — local Ubuntu 22.04 binaries need glibc 2.35, Bohrium Ubuntu 20.04 has glibc 2.31
  5. **APT install with retries**: OF9 installed OK (SourceForge worked on retry), but `source /opt/openfoam9/etc/bashrc` fails under `set -e` — a known issue where OF bashrc returns non-zero
- Tried: 5 different approaches total. Current fix: `set +e` around `source bashrc`, then `set -e` again. This is a well-known OpenFOAM gotcha.
- Root cause pattern: Each failure reveals the next layer of container incompatibility. The final script (compile from source on Bohrium + `set +e` for bashrc) addresses all discovered issues.

### EARS — Progress (2026-03-28 16:42)
- **Decision**: User will build a custom Docker image from our Dockerfile and push to `registry.dp.tech`. This eliminates all runtime installation/compilation overhead on Bohrium.
- **Correction**: dynamicMesh2D/dynamicFvMesh2D DO compile on Foundation OF9 (PackedBoolList and 4-arg writeObject are still supported). My earlier analysis confused Foundation OF9 with ESI OpenFOAM. All 5 targets compiled locally on OF9 — confirmed by checking `$FOAM_USER_LIBBIN`. User correctly pointed out these libs will be needed for future AMR cases.
- **Dockerfile updated**: All 4 libraries + solver compiled in image (fluxSchemes_improved, DLBFoam, dynamicMesh2D, dynamicFvMesh2D, detonationFoam_V2.0). controlDict libs entries restored.
- **Waiting on**: User to build & push Docker image, then provide the registry address.
