# detonationFoam Architecture

## Source File Map

```
detonationFoam_V2.0.C                    # main() -- entry point
├── createFields.H                        # Construct all fields + fluxScheme
├── createFieldRefs.H                     # Aliases: p, T, psi, inertIndex
│
├── solverTypeEuler/                      # INVISCID path
│   ├── solverTypeEuler.H                 # Time loop
│   ├── rhoEqn_Euler.H                   #   ddt(rho) + div(rhoPhi) = 0
│   ├── rhoUEqn_Euler.H                  #   ddt(rhoU) + div(rhoUPhi) = 0
│   ├── rhoYEqn_Euler.H                  #   ddt(rho*Yi) + div(rhoPhi*Yi) = R(Yi)
│   └── rhoEEqn_Euler.H                  #   ddt(rhoE) + div(rhoEPhi) = Qdot
│
├── solverTypeNS_Sutherland/              # VISCOUS + Fick diffusion
│   ├── solverTypeNS_Sutherland.H         # Time loop
│   ├── rhoEqn_NS.H                      #   same continuity
│   ├── rhoUEqn_NS.H                     #   + Laplacian(muEff,U) + div(tauMC)
│   ├── rhoYEqn_NS.H                     #   + divj(Yi) (Fick)
│   └── rhoEEqn_NS.H                     #   - div(sigmaDotU) + divq(e)
│
├── solverTypeNS_mixtureAverage/          # FULL multicomponent transport
│   ├── solverTypeNS_mixtureAverage.H     # Time loop + transport calc
│   ├── transport/                        #   Binary diffusion, mixing rules
│   ├── rhoEqn_NS.H, rhoUEqn_NS.H        #   same as Sutherland
│   ├── rhoYEqn_NS_mixtureAverage.H       #   + multicomponent diffusion + Soret
│   └── rhoEEqn_NS_mixtureAverage.H       #   + species enthalpy diffusion flux
│
└── fluxSchemes_improved/                 # RIEMANN SOLVER LIBRARY
    ├── fluxScheme/fluxScheme.H           #   Abstract base class
    ├── fluxScheme/fluxScheme.C           #   update() -- face reconstruction + flux loop
    ├── HLLC/HLLC.C                       #   HLLC Riemann solver
    ├── Kurganov/Kurganov.H               #   Kurganov-Tadmor central-upwind
    ├── HLL/, HLLCP/, Tadmor/             #   Other solvers
    ├── AUSMPlus/, AUSMPlusUp/            #   AUSM family
    └── RiemannConvectionScheme/          #   Adapter for fvMatrix system
```

## Algorithm Flow (one timestep)

```
┌─────────────────────────────────────────────┐
│ 1. detoCellular.H                           │
│    - Update max-pressure field               │
│    - Compute density gradient (schlieren)     │
│    - Adjust deltaT via CFL                   │
├─────────────────────────────────────────────┤
│ 2. mesh.update()  (AMR if enabled)           │
├─────────────────────────────────────────────┤
│ 3. fluxScheme->update()                      │
│    ┌───────────────────────────────────────┐ │
│    │ For each face:                        │ │
│    │  a. Reconstruct rho,rhoU,e,c,rPsi     │ │
│    │     to owner/neighbour via limiter     │ │
│    │  b. Call Riemann solver (e.g. HLLC)   │ │
│    │  c. Output: rhoPhi, rhoUPhi, rhoEPhi  │ │
│    └───────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│ 4. Solve conservation equations:             │
│    a. Continuity:  ddt(rho) + div(rhoPhi)    │
│    b. Momentum:    ddt(rhoU) + div(rhoUPhi)  │
│       [+viscous for NS]                      │
│    c. Species:     ddt(rho*Yi) + div(...)     │
│       + reaction->R(Yi)  [+diffusion for NS] │
│    d. Energy:      ddt(rhoE) + div(rhoEPhi)  │
│       + reaction->Qdot() [+conduction for NS]│
├─────────────────────────────────────────────┤
│ 5. Reconstruct primitives:                   │
│    U = rhoU/rho                              │
│    e = rhoE/rho - 0.5*|U|^2                 │
│    thermo.correct() -> T from e              │
│    p = rho / psi                             │
├─────────────────────────────────────────────┤
│ 6. Write fields if scheduled                 │
│ 7. Check SW_position_limit for early exit    │
└─────────────────────────────────────────────┘
```

## HLLC Riemann Solver -- Wave Structure

```
     SOwn          SStar          SNei
  ---|--------------|--------------|---  -> x
  Left(Own)    Left*    Right*    Right(Nei)
  region       region   region    region
```

- **SOwn, SNei**: fastest left/right wave speeds (estimated from Roe averages)
- **SStar**: contact wave speed (from pressure balance)
- 4 regions: supersonic-left, star-left, star-right, supersonic-right
- Flux = weighted combination based on which region the face sits in

## Key OpenFOAM Patterns Used

| Pattern | Where | Purpose |
|---------|-------|---------|
| `runTimeSelectionTable` | fluxScheme | Runtime-pluggable Riemann solvers |
| `#include "header.H"` | solver types | Code reuse without classes |
| `fvm::ddt + fvc::div` | equation files | Implicit time + explicit convection |
| `psiReactionThermo` | createFields | Compressibility-based thermo |
| `CombustionModel<>` | createFields | Provides Qdot and R(Yi) |
| `directionInterpolate` | fluxScheme | Owner/neighbour face reconstruction |

## Data Flow Between Components

```
thermophysicalProperties -> psiReactionThermo -> { p, T, e, psi, gamma, Y[] }
                                                       |
chemistryProperties -> CombustionModel --> Qdot, R(Yi) -+
                                                       |
fvSchemes::fluxScheme -> fluxScheme::update() --> rhoPhi, rhoUPhi, rhoEPhi
                                                       |
                        Conservation equations <-------+
                               |
                        Primitive reconstruction -> { U, e, T, p }
```

## NS Two-Step Solve Pattern (verified from source)

The NS variants use a **two-step explicit-then-implicit** approach:
1. **Explicit step**: solve `ddt(rhoU) + div(rhoUPhi) = 0` -> reconstruct U = rhoU/rho
2. **Implicit correction**: solve `ddt(rho,U) - ddt(rho,U) - laplacian(muEff,U) - div(tauMC) = 0`
   - The `ddt - ddt` trick makes RHS = just the viscous terms (net time derivative cancels)
3. Update `rhoU = rho*U` after the correction

Same pattern for energy: explicit convective step, then implicit conduction correction.

## NS_mixtureAverage -- Key Implementation Details (from source)
- **Soret effect** is only implemented for H and H2 species (hard-coded species names)
- **Correction velocity** `DiffError`/`phiUc`: sums all species diffusion fluxes; applied as
  a correction convection term `mvConvection->fvmDiv(phiUc, Yi)` to ensure sum(Yi)=1
- **Species enthalpy flux** `vk`: accumulates `Hs_i * speciesFlux_i` for the energy equation
- `Qdot` source term enters in the **implicit correction** energy step (not the explicit part)
- Binary diffusion coefficients stored as polynomial fits: `Dij = f(log(T))`, pressure-scaled

## DLBFoam Load Balancing Algorithm
1. Each rank computes total cpuTime from previous timestep chemistry
2. `allGather` broadcasts loads across all ranks
3. Two-pointer algorithm: heaviest rank sends problems to lightest, advancing pointers
4. Problems serialized via `ChemistryProblem` structs over non-blocking MPI
5. Each rank solves local + received problems; solutions sent back via reverse mapping
6. Previous cpuTime used as proxy for current cost (chemistry stiffness changes slowly)

## ROUND Limiters -- Why Less Dissipative
- Standard Minmod: `psi(r) = min(r, 1)` -- hugs **lower** TVD boundary (most dissipative)
- ROUND schemes: smooth rational functions hugging **upper** TVD boundary
- Beta parameters (500-1100) control steepness of transition around r=1
- Lambda parameter caps max limiter value: `2 - 2*lambda` (smaller lambda = less dissipation)
- 8th-order polynomial smoothness avoids spurious oscillations at limiter kinks

## 2D AMR (dynamicRefineFvMesh2D)
- `hexRef82D` splits cells into 4 (not 8) -- only edges on empty-patch faces are divisible
- Refinement criteria: user-specified field (e.g. density gradient) between thresholds
- Buffer layers (`nBufferLayers`) propagate refinement candidates via cell-face-cell
- 2:1 level balance enforced via `consistentRefinement()`
- Unrefinement: cells merge back to parent when field < `unrefineLevel`
