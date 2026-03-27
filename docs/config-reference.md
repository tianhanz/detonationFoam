# detonationFoam Configuration Reference

Every input file knob, what it does, and recommended values.

---

## 1. `constant/solverTypeProperties`

| Parameter | Values | Effect |
|-----------|--------|--------|
| `solverType` | `Euler` / `NS_Sutherland` / `NS_mixtureAverage` | Selects equation set |
| `SW_position_limit` | float (meters) | Solver exits when leading shock reaches this x-position. Set > domain length to disable |

---

## 2. `system/controlDict`

| Parameter | Typical value | Effect |
|-----------|--------------|--------|
| `application` | `detonationFoam_V2.0` | Solver executable name |
| `deltaT` | `1e-11` | Initial time step (s). Must be tiny for detonation start |
| `endTime` | `300e-6` | Simulation end time (s) |
| `adjustTimeStep` | `yes` | Enable adaptive time stepping |
| `maxCo` | `0.1` | Max convective Courant number |
| `maxAcousticCo` | `0.1` | Max acoustic Courant number (for detonation!) |
| `useAcousticCourant` | `yes` | Use speed-of-sound in CFL. **Critical for detonation** |
| `maxDeltaT` | `1e-6` | Upper bound on time step |
| `writeControl` | `adjustableRunTime` | Write at physical time intervals |
| `writeInterval` | `1e-7` | Time between field writes |
| `writePrecision` | `12` | Digits in output. 12 recommended for detonation |
| `timePrecision` | `12` | Digits in time directory names |
| `libs (...)` | list of .so | Runtime-loaded libraries (DLBFoam, dynamic mesh, etc.) |

### Dynamic libraries to load
```
libs
(
    "libdynamicMesh2D.so"      // 2D AMR (optional)
    "libdynamicFvMesh2D.so"    // 2D AMR mesh (optional)
    "libchemistryModel_DLB.so" // DLBFoam load balancing (optional)
    "libODE_DLB.so"            // DLBFoam ODE solver (optional)
);
```

---

## 3. `system/fvSchemes`

### Flux scheme (Riemann solver)
```
fluxScheme    Kurganov;   // Options: Kurganov, HLLC, HLL, HLLCP, Tadmor, AUSMPlus, AUSMPlusUp
```

| Scheme | Character | Best for |
|--------|-----------|----------|
| `Kurganov` | Central-upwind, diffusive, robust | General use, startup |
| `HLLC` | Upwind, sharp shocks | Production runs, shock-sensitive studies |
| `HLL` | Upwind, more diffusive than HLLC | Stability-critical cases |
| `HLLCP` | HLLC variant | Carbuncle-sensitive flows |
| `AUSMPlus` | Low-dissipation for contact | Mixed subsonic/supersonic |
| `AUSMPlusUp` | All-speed AUSM+ | Low-Mach + detonation |
| `Tadmor` | Most diffusive central | Debug / stability baseline |

### Reconstruction limiters
```
interpolationSchemes
{
    reconstruct(rho)   Minmod;        // scalar limiter
    reconstruct(rhoU)  MinmodV;       // vector limiter (V suffix)
    reconstruct(rPsi)  Minmod;
    reconstruct(e)     Minmod;
    reconstruct(c)     Minmod;
}
```

| Limiter | Dissipation | Notes |
|---------|-------------|-------|
| `Minmod` / `MinmodV` | High (safe) | Default, good for startup |
| `vanLeer` / `vanLeerV` | Medium | Better accuracy |
| `ROUNDA` / `ROUNDAV` | Low | Structure-preserving, needs ROUNDSchemes lib |
| `ROUNDAplus` | Low, bounded [0,1] | For mass fractions |
| `ROUNDF`, `ROUNDL` | Very low | Advanced, may need lower CFL |

### Other schemes
```
ddtSchemes       { default Euler; }           // Only Euler (1st order time) supported
gradSchemes      { default cellLimited Gauss linear 0.7; }  // 0.7 = limiter coefficient
divSchemes       { default Gauss linear; div(rhoPhi,Yi_h) Gauss limitedLinear 1; }
laplacianSchemes { default Gauss linear corrected; }
snGradSchemes    { default corrected; }
```

---

## 4. `system/fvSolution`

```
solvers
{
    "(rho|rhoU|rhoE)"           // Explicit: diagonal solver
    {
        solver          diagonal;
    }
    "(U|e)"                     // Implicit corrections (symmetric)
    {
        solver          PBiCGStab;
        preconditioner  DIC;
        tolerance       1e-12;
        relTol          0.1;       // 0 in "Final" sub-dict
    }
    "(Yi)"                      // Species (asymmetric)
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-12;
        relTol          0;
    }
}
```

---

## 5. `constant/thermophysicalProperties`

```
thermoType
{
    type            hePsiThermo;            // Compressibility-based (psi = 1/RT)
    mixture         multiComponentMixture;  // Multi-species
    transport       sutherland;             // Sutherland viscosity model
    thermo          janaf;                  // JANAF polynomial thermodynamics
    energy          sensibleInternalEnergy; // Solve for e (not h)
    equationOfState perfectGas;             // Ideal gas EOS
    specie          specie;                 // Standard specie class
}

inertSpecie AR;   // Species computed as 1 - sum(others). Must be in species list.
```

### Included data files
```
#include "$FOAM_CASE/constant/foam/species.foam"    // Species list
#include "$FOAM_CASE/constant/foam/thermo.foam"     // JANAF coefficients per species
```

---

## 6. `constant/chemistryProperties`

| Parameter | Typical value | Effect |
|-----------|--------------|--------|
| `chemistry` | `on` / `off` | Enable/disable reactions |
| `initialChemicalTimeStep` | `1` | Starting chemistry sub-step (s) |
| `chemistryType.solver` | `ode` | Chemistry solver type |
| `chemistryType.method` | `loadBalanced` / `standard` | DLBFoam or standard |
| `odeCoeffs.solver` | `seulex` / `Rosenbrock34` | ODE integrator |
| `odeCoeffs.absTol` | `1e-6` to `1e-10` | Absolute tolerance for ODE |
| `odeCoeffs.relTol` | `1e-3` to `1e-4` | Relative tolerance for ODE |
| `differentialDiffusion` | `on` / `off` | Species-specific diffusion coefficients |
| `thermalDiffusion` | `on` / `off` | Soret effect (thermal diffusion) |
| `Prt` | `0.7` | Turbulent Prandtl number |
| `Sct` | `0.7` | Turbulent Schmidt number |

### Load balancing (DLBFoam)
```
loadbalancing
{
    active    true;   // Enable MPI load balancing for chemistry
    log       false;  // Print load balancing stats
}
```

### Reference mapping (DLBFoam)
```
refmapping
{
    // Maps similar cells to avoid redundant ODE solves
    // Empty = disabled
}
```

---

## 7. `constant/combustionProperties`

```
combustionModel  laminar;   // Only laminar supported in detonationFoam
```

---

## 8. `constant/momentumTransport`

```
simulationType  laminar;   // or RAS, LES
```
For detonation DNS: use `laminar`. For RANS: `RAS` with a model like `kEpsilon`.

---

## 9. Initial Condition Files (`0/` directory)

Each field file needs:
- `internalField`: uniform or nonUniform initial value
- `boundaryField`: boundary conditions for each patch

### Common boundary conditions for detonation
| Patch type | For walls | For inlet/outlet |
|------------|-----------|-----------------|
| `zeroGradient` | p, T, Yi | outflow |
| `fixedValue` | U (no-slip) | inflow |
| `slip` | U (free-slip) | -- |
| `waveTransmissive` | -- | non-reflecting outflow |
| `empty` | -- | 2D front/back faces |

---

## 10. `system/setFieldsDict`

Used to patch a high-P/high-T driver region to initiate detonation:
```
defaultFieldValues
(
    volScalarFieldValue T 300       // ambient temperature
    volScalarFieldValue p 101325    // ambient pressure
);
regions
(
    boxToCell
    {
        box (0 -1 -1) (0.005 1 1);   // driver region: x < 5mm
        fieldValues
        (
            volScalarFieldValue T 2000      // hot driver
            volScalarFieldValue p 9.12e6    // high pressure driver
        );
    }
);
```

---

## Parameter Sensitivity Guide

| Parameter | If too large | If too small |
|-----------|-------------|-------------|
| `maxCo` | Simulation blows up | Unnecessarily slow |
| `deltaT` (initial) | Ignition instability | Wastes startup time (harmless) |
| `odeCoeffs.absTol` | Inaccurate chemistry, wrong detonation speed | Very slow chemistry solve |
| `odeCoeffs.relTol` | Wrong species profiles | Slow |
| `gradSchemes limiter` (0-1) | More dissipative gradients | Less stable |
| `SW_position_limit` | Simulation runs too long | Stops before interesting physics |
| Driver region size | Over-driven detonation | Fails to initiate |
| Driver pressure | Over-driven, non-physical transients | Fails to initiate |
