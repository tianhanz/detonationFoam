# Reproduction Trace — sun-2023-cpc-292

## 2026-03-30 — Directory scaffolded
- Paper: detonationFoam: An open-source solver for simulation of gaseous detonation based on OpenFOAM
- Tier A, WTS 14
- Status: NOT_STARTED

### EARS — Session Start (2026-03-30 15:40)
- Task: Reproduce Paper [2] (Sun 2023 CPC) — 5-phase workflow starting with CJ reference computation
- Why: Validate the detonationFoam paper reproduction pipeline using the solver paper as sentinel case

### Phase 0-1: Parameter extraction (2026-03-30 15:42)
- Extracted all parameters from existing cases (1D_H2O2_detonation, 2D_H2O2_cellular)
- 1D: 20cm tube, dx=5μm, 40K cells, endTime=50μs, HLLC, Euler, Rosenbrock34
- 2D: 10cm×2cm channel, dx=dy=20μm, 5M cells, endTime=100μs, cyclic top/bottom
- Both: stoich H2/air (2H2+O2+3.76N2), T0=300K, P0=1atm, hot spot at 30atm/2500K
- Mechanism: 11sp/27rxn (Burke 2011), but Cantera h2o2.yaml has 10sp/29rxn
- Paper PDF not available locally — figure list estimated from solver paper structure (8 figures)

### Phase 2: Independent reference (2026-03-30 15:55)
- **Method**: Pressure-sweep on equilibrium Hugoniot (5000 pts, P2/P0=8-25)
- **Mechanism**: Cantera h2o2.yaml (10sp/29rxn) — close to Burke 2011
- **Results**:
  - V_CJ = 1976.32 m/s (0.42% vs literature 1968)
  - P_CJ = 15.573 atm (0.17% vs literature 15.6)
  - T_CJ = 2964.7 K (0.50% vs literature 2950)
- **Verdict**: PASS — all errors < 1%
- Saved to data/cj_reference.json

### Phase 3: Target computation (2026-03-30, running)
- Bohrium jobs submitted:
  - 1D (Job 22333336): Running, t=2.62μs at 2.4hr, shock at 10.2mm, T_max=3660K
  - 2D AMR (Job 22332935): Running, t=1.4μs at ~76min, shock at 7.8mm
- Both stable with Rosenbrock34, no FPE
- Will extract CJ velocity from shock trajectory once enough data accumulated

### Phase 3 results (2026-03-31)
- Both Bohrium jobs finished (hit 6hr time limit):
  - 1D (Job 22333336): t=4.31μs/50μs, shock at 13.5mm, ClockTime=21680s
  - 2D AMR (Job 22332935): t=4.48μs/5μs, 11875 cells with AMR, ClockTime~21600s
- **CJ velocity extracted from 1D shock trajectory**:
  - Linear fit of 8 data points (t > 0.5μs): **V = 1978.9 m/s**
  - Error vs Cantera CJ: 0.13%, vs literature: 0.56%
  - Instantaneous velocity converged to 1976-1980 m/s after 0.5μs
  - **Verdict: PASS**
- 2D AMR test showed stable AMR operation with Rosenbrock34, no FPE
- Remaining: 1D needs longer run for full profile; 2D cellular (5M cells) needs c32 machine

### EARS — Progress (2026-03-31 11:33)
- Paper PDF inaccessible (web blocked) — extracted all numerical setup from existing case files instead
- Designing grid convergence study (Fig 8): 5 cases in 1D geometry (5cm domain, 10μs endTime)
  - 4 uniform: dx = 40, 20, 10, 5 μm (1250 to 10000 cells)
  - 1 AMR: base 40μm + 2 levels → effective 10μm (compare against uniform_dx10)
- Writing gen_convergence_cases.py to scaffold all 5 cases automatically
- Will compare: CJ velocity, peak pressure, ZND induction length, p/T profiles
- Decision: Use 1D (not 2D) for convergence — isolates numerical error from multidimensional effects, much cheaper

### Grid convergence jobs submitted (2026-03-31 11:39)
- 5 cases created in `case/` directory via `scripts/gen_convergence_cases.py`:
  - uniform_dx40: 1250 cells, dx=40μm, max_time=60min → ~~Job 22340991~~ failed
  - uniform_dx20: 2500 cells, dx=20μm, max_time=120min → ~~Job 22340969~~ failed
  - uniform_dx10: 5000 cells, dx=10μm, max_time=240min → ~~Job 22340971~~ failed
  - uniform_dx05: 10000 cells, dx=5μm, max_time=360min → ~~Job 22340974~~ failed
  - amr_base40_L2: 1250 base cells + 2 AMR levels (eff 10μm), max_time=240min → ~~Job 22340977~~ failed
- **Root cause**: chemistryProperties missing `#include "$FOAM_CASE/constant/foam/reactions.foam"` — solver couldn't find reactions dict
- **Fix**: Added `#include` to gen_convergence_cases.py, regenerated all cases

### Grid convergence resubmitted (2026-04-01 09:39)
- Jobs 22347161–65 failed again: fvSolution had empty `solvers {}` — solver needs `rho` diagonal solver entry
- **Fix**: Added full fvSolution solvers block (rho/rhoU/rhoE diagonal, U/e PBiCGStab, Yi PBiCGStab)
- **Added preflight check** to `submit_detonation.py`: runs blockMesh + setFields + 2 solver steps locally before any Bohrium submission — would have caught both bugs instantly
- Regenerated cases, preflight PASSED for both uniform and AMR

### Grid convergence final submission (2026-04-01 10:01)
- Job IDs: 22347187 (dx40), 22347191 (dx20), 22347188 (dx10), 22347194 (dx05), 22347189 (AMR)
- All preflight-validated locally before submission
- Next: check job results, run analyze_convergence.py, generate convergence plots
