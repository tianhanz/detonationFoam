# detonationFoam Learning Path

A progressive curriculum: each level builds on the previous. Complete all checkpoints before advancing.

---

## Level 1: Orientation (Read-only)
**Goal**: Understand what the solver does and how a case is organized.

### Study material
1. Read `README.md` — project scope, publications, feature list
2. Browse `tutorials/1D_NH3_O2_cracking_0.3_detonation/` — standard OpenFOAM case layout
3. Read `constant/solverTypeProperties` — the solver-type switch

### Key concepts
- OpenFOAM case structure: `0/` (initial conditions), `constant/` (physics), `system/` (numerics)
- The 3 solver types: Euler, NS_Sutherland, NS_mixtureAverage
- What CJ detonation is (Chapman-Jouguet theory)
- What a detonation cell is (triple-point trajectories in 2D)

### Checkpoints
- [ ] Can explain what each directory in the tutorial case does
- [ ] Can name the 3 solver types and when to use each
- [ ] Can describe the physical problem the tutorial solves (1D NH3/O2 detonation)

---

## Level 2: Configuration Literacy
**Goal**: Understand every input file and what each parameter controls.

### Study material (read these files in the tutorial)
1. `system/controlDict` — time control, CFL, write settings, dynamic libraries
2. `system/fvSchemes` — flux scheme selection, reconstruction limiters, discretization
3. `system/fvSolution` — linear solvers (diagonal for explicit, iterative for implicit)
4. `constant/thermophysicalProperties` — EOS, thermo model, transport model, species
5. `constant/chemistryProperties` — ODE solver, tolerances, load balancing, diffusion
6. `constant/combustionProperties` — combustion model (laminar)
7. `constant/foam/reactions.foam` — reaction mechanism (Arrhenius parameters)
8. `0/p`, `0/T`, `0/U`, `0/NH3`, etc. — initial + boundary conditions

### Key concepts
- `fluxScheme` in fvSchemes controls the Riemann solver
- `reconstruct(*)` entries control face-value interpolation (limiters: Minmod, vanLeer, ROUND)
- `maxCo 0.1` — typical CFL for detonation (acoustic Courant)
- `adjustTimeStep yes` + `useAcousticCourant yes` — adaptive time stepping
- `deltaT 1e-11` — initial tiny timestep for detonation ignition
- `inertSpecie AR` — the species computed as 1-sum(others)
- `seulex` ODE solver with `absTol 1e-6`, `relTol 1e-3` — chemistry integration

### Checkpoints
- [ ] Can explain what changing `fluxScheme` from Kurganov to HLLC does
- [ ] Can explain why maxCo is 0.1 (not 0.5 or 1.0)
- [ ] Can trace how species thermo data flows: thermo.foam -> thermophysicalProperties -> solver
- [ ] Can explain what `SW_position_limit` does (early exit when shock reaches position)

---

## Level 3: Solver Internals
**Goal**: Read and understand the C++ source code flow.

### Study material (read these source files)
1. `detonationFoam_V2.0.C` — main(), solver type branching
2. `createFields.H` — field construction order, fluxScheme instantiation
3. `solverTypeEuler/solverTypeEuler.H` — simplest time loop (start here)
4. `solverTypeEuler/rhoEqn_Euler.H` — continuity equation
5. `solverTypeEuler/rhoUEqn_Euler.H` — momentum equation
6. `solverTypeEuler/rhoYEqn_Euler.H` — species transport + reaction source
7. `solverTypeEuler/rhoEEqn_Euler.H` — energy equation + Qdot
8. `fluxSchemes_improved/fluxScheme/fluxScheme.H` and `.C` — abstract base, update() loop
9. `fluxSchemes_improved/HLLC/HLLC.C` — HLLC Riemann solver implementation

### Key concepts
- Explicit density-based approach: fluxes computed first, then conservation laws solved
- `fluxScheme::update()` populates phi, rhoPhi, rhoUPhi, rhoEPhi for all faces
- HLLC wave speed estimation: SOwn, SNei, SStar — 4-region solution
- Operator splitting: convection (explicit from Riemann) + diffusion/source (implicit)
- `thermo.correct()` reconstructs T from internal energy e
- Species clamping: Yi = max(Yi, 0) prevents negative mass fractions

### Checkpoints
- [ ] Can trace the flow: main() -> createFields -> time loop -> flux update -> equation solves
- [ ] Can explain what `fluxScheme::update()` does step by step
- [ ] Can describe the difference between Euler and NS_Sutherland equation files
- [ ] Can explain how reaction source terms enter (reaction->R(Yi), reaction->Qdot())

---

## Level 4: Viscous & Transport Extensions
**Goal**: Understand the NS variants and multicomponent transport.

### Study material
1. `solverTypeNS_Sutherland/solverTypeNS_Sutherland.H` — viscous time loop
2. `solverTypeNS_Sutherland/rhoUEqn_NS.H` — momentum with viscous stress
3. `solverTypeNS_Sutherland/rhoEEqn_NS.H` — energy with heat conduction
4. `solverTypeNS_mixtureAverage/solverTypeNS_mixtureAverage.H` — mixture-averaged transport
5. `solverTypeNS_mixtureAverage/transport/*.H` — binary diffusion, mixing rules

### Key concepts
- Sutherland viscosity: mu = As * sqrt(T) / (1 + Ts/T)
- Viscous stress tensor: tau = mu*(grad(U) + grad(U)^T) - 2/3*mu*div(U)*I
- `sigmaDotU` = viscous work term in energy equation
- Mixture-averaged diffusion: Dij from kinetic theory, correction velocity for mass conservation
- Soret effect (thermalDiffusion): species diffuse due to temperature gradients
- These transport property files are read from external binary/text files

### Checkpoints
- [ ] Can identify all additional terms in NS vs Euler equations
- [ ] Can explain Fick diffusion vs mixture-averaged multicomponent diffusion
- [ ] Can explain what the Soret effect is and when it matters
- [ ] Can describe when NS_mixtureAverage is worth the extra cost

---

## Level 5: Advanced Features
**Goal**: Understand DLBFoam, ROUNDSchemes, dynamic mesh refinement.

### Study material
1. `DLBFoam-1.0-1.0_OF8/` — LoadBalancedChemistryModel, LoadBalancer
2. `ROUNDSchemes/src/` — ROUNDA, ROUNDAplus limiter functions
3. `dynamicMesh2D/` — hexRef82D, dynamicRefineFvMesh2D

### Key concepts
- **DLBFoam**: redistributes chemistry ODE problems across MPI ranks to equalize CPU load
  - ChemistryProblem/Solution structs serialized via MPI
  - Reference cell mapping avoids redundant ODE solves for similar cells
- **ROUNDSchemes**: structure-preserving limiters (less numerical dissipation than Minmod)
  - ROUNDA: general purpose; ROUNDAplus: bounded [0,1] for mass fractions
- **dynamicMesh2D**: adaptive mesh refinement for 2D cases
  - Refine where gradients are large; coarsen where flow is smooth
  - `hexRef82D` constrains refinement to 2D plane

### Checkpoints
- [ ] Can explain the DLBFoam load-balancing algorithm conceptually
- [ ] Can explain why ROUND limiters give less dissipation than Minmod
- [ ] Can describe how to enable AMR in a 2D case

---

## Level 6: Practice -- Running Simulations
**Goal**: Set up, run, modify, and diagnose real simulations.

### Practice exercises (progressive difficulty)

#### Exercise 1: Run the tutorial as-is
```
cd tutorials/1D_NH3_O2_cracking_0.3_detonation
blockMesh
setFields
detonationFoam_V2.0
```
- Verify detonation propagation in results
- Plot pressure profile at different times

#### Exercise 2: Switch flux scheme
- Change `fluxScheme Kurganov` to `fluxScheme HLLC` in fvSchemes
- Run again, compare shock sharpness

#### Exercise 3: Switch solver type
- Change `NS_Sutherland` to `Euler` in solverTypeProperties
- Compare results -- viscous effects should disappear

#### Exercise 4: Modify initial conditions
- Change driver section pressure/temperature in setFieldsDict
- Observe effect on detonation initiation

#### Exercise 5: Change chemistry
- Modify ODE tolerances (tighten absTol to 1e-8)
- Observe effect on accuracy vs cost

#### Exercise 6: Set up a new case from scratch
- Choose a different fuel (H2/O2 or CH4/O2)
- Build the case directory, reaction mechanism, initial conditions
- Run and validate against CJ theory

#### Exercise 7: 2D detonation cell simulation
- Extend to 2D domain
- Enable detoCellular tracking
- Visualize detonation cell structure

### Checkpoints
- [ ] Successfully ran tutorial case end-to-end
- [ ] Can compare results between flux schemes
- [ ] Can modify initial conditions and predict the effect
- [ ] Can set up a case from scratch for a new fuel
- [ ] Can diagnose and fix a crashing simulation
