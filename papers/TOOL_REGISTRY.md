# Tool Registry — detonationFoam Paper Reproduction

## Solver: detonationFoam V2.0

**Reference**: Sun et al., Computer Physics Communications 292 (2023) 108859
**OpenFOAM version**: 9 (ported from 8)
**Docker image**: `registry.dp.tech/dptech/dp/native/prod-1408/detonationfoam:0.2`

### Equation Sets

| Mode | Key | Transport | Use case |
|------|-----|-----------|----------|
| Euler (inviscid) | `Euler` | None | Detonation propagation, cellular structure |
| NS-Sutherland | `NS_Sutherland` | Sutherland viscosity | Viscous detonation, boundary layers |
| NS-mixtureAverage | `NS_mixtureAverage` | Multicomponent + Soret | Detailed transport, diffusion flames |

### Flux Schemes

| Scheme | Order | Recommended use |
|--------|-------|-----------------|
| **HLLC** | 2nd (MUSCL) | Default for detonation — robust, accurate |
| HLL | 2nd (MUSCL) | More diffusive, use if HLLC oscillates |
| HLLCP | 2nd (MUSCL) | Pressure-based variant |
| Kurganov | 2nd | Central scheme, less dissipative |
| AUSMPlus | 2nd | Low-Mach compatible |
| AUSMPlusUp | 2nd | All-speed variant |
| Tadmor | 2nd | Entropy-stable central |

### Reconstruction

- MUSCL with Minmod limiter (default)
- MUSCL with vanLeer limiter

### Time Integration

- 1st order Euler (explicit)
- CFL-based adaptive time stepping

### ODE Solvers (chemistry)

| Solver | Stability | Recommended |
|--------|-----------|-------------|
| **Rosenbrock34** | L-stable, 3rd order | **Yes** — no extrapolation, safe with JANAF |
| seulex | Extrapolation | **No** — causes FPE when T > 6000K |

### AMR

- `dynamicRefineFvMesh2D` — 2D adaptive mesh refinement
- Refinement/unrefinement based on gradient criteria
- **2D only** — no bundled 3D AMR

### Boundary Conditions

Standard OpenFOAM: `zeroGradient`, `fixedValue`, `cyclic`, `symmetryPlane`, `empty` (2D), `wall`

## Chemical Mechanisms

### Available (in repository)

| Mechanism | Species | Reactions | File location | Papers |
|-----------|---------|-----------|---------------|--------|
| **Burke 2011 H2/O2** | 11 | 27 | `cases/1D_H2O2_detonation/constant/foam/` | Tier A: [2],[7],[11],[17],[21] |
| **NH3/O2 (cracking)** | 33 | — | `tutorials/1D_NH3_O2_cracking_0.3_detonation/constant/foam/` | Tier B: [14],[16] (may need extension) |

### Needed (to be sourced)

| Mechanism | Species (est.) | Source | Papers |
|-----------|---------------|--------|--------|
| NH3/H2/air (Stagni or Song) | 30-60 | Public database / paper supplement | [6] |
| n-C12H26/air (reduced) | 30-55 | Yao or LLNL reduced | [13] |
| C2H4/O2/O3 (ethylene-ozone) | 30-50 | Paper [20] supplement | [20] |

### Mechanism Conversion

```bash
python bohrium/chemkin2foam.py \
    --chem <path>/chem.inp \
    --therm <path>/therm.dat \
    --tran <path>/tran.dat \
    --output <case>/constant/foam/
```

## Independent Reference Tools

| Tool | Use | Installation |
|------|-----|-------------|
| **Cantera** | 0D ignition, equilibrium, CJ properties | `pip install cantera` |
| **SDToolbox** | CJ velocity, ZND structure | `pip install sdtoolbox` |

### Key Validation Quantities

| Quantity | Reference method | Acceptance |
|----------|-----------------|------------|
| CJ velocity | SDToolbox `CJspeed()` | < 2% error |
| CJ pressure | SDToolbox `PostShock_eq()` | < 5% error |
| Induction length | SDToolbox `zndsolve()` | < 10% error |
| Ignition delay time | Cantera `IdealGasReactor` | < 5% error |
| Cell size (λ) | Literature correlation | < 20% (inherent scatter) |

## Compute Resources (Bohrium)

| Machine | Cores | RAM | Use case | Cost/hr |
|---------|-------|-----|----------|---------|
| `c4_m8_cpu` | 4 | 8 GB | 1D cases, quick 2D tests | Low |
| `c8_m16_cpu` | 8 | 16 GB | Standard 2D cases | Medium |
| `c32_m64_cpu` | 32 | 64 GB | Large 2D, cellular structure | High |
| `c64_m128_cpu` | 64 | 128 GB | 3D cases | Very high |

### Job Submission

```bash
python3 bohrium/submit_detonation.py <case_dir> --np <cores> --machine <type>
```
