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
