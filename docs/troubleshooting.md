# detonationFoam Troubleshooting

Common problems, their root causes, and how to fix them.

---

## Compilation: OpenFOAM Version Compatibility

detonationFoam is built for **OpenFOAM 8** (openfoam.org Foundation version).

### OF9 compatibility (tested)
- **fluxSchemes_improved**: Compiles OK on OF9
- **dynamicMesh2D**: Compiles OK on OF9 (warnings only)
- **DLBFoam**: FAILS -- `kinematicTransportModel.H` not found (OF9 refactored thermo transport)
- **Main solver**: FAILS -- `fluidThermoMomentumTransportModel.H` not found

### OF9 header renames (key breaking changes)
| OF8 header | OF9 equivalent |
|-----------|---------------|
| `fluidThermoMomentumTransportModel.H` | removed/refactored |
| `psiReactionThermophysicalTransportModel.H` | `fluidReactionThermophysicalTransportModel.H` |
| `CombustionModel.H` | `combustionModel.H` |

### Recommendation
Install OpenFOAM 8 (`openfoam8` package) or use Docker: `openfoam/openfoam8-paraview56`.

---

## Crash: Floating Point Exception (SIGFPE)

### Symptoms
```
#0 Foam::error::printStack(Foam::Ostream&)
--> FOAM FATAL ERROR: Floating point exception
```

### Common causes & fixes

| Cause | Diagnosis | Fix |
|-------|-----------|-----|
| CFL too high | Check `Courant Number` in log -- spikes above 1 | Lower `maxCo` (try 0.05) |
| Initial deltaT too large | Crash at first timestep | Lower `deltaT` to 1e-12 |
| Bad initial conditions | Crash immediately after setFields | Check species sum to 1.0, positive p and T |
| Negative species | Log shows Yi < 0 warnings before crash | Check species clamping, reduce CFL |
| Incompatible boundary conditions | Crash at boundaries | Check all patches have consistent BC types |
| Chemistry stiffness | Crash during chemistry solve | Tighten ODE tolerances or use `seulex` solver |
| Driver too strong | Extremely high pressures blow up | Reduce driver pressure closer to CJ value |

---

## Crash: "Maximum number of iterations exceeded"

### Cause
Iterative linear solver (PBiCGStab) didn't converge for the implicit correction step.

### Fix
```
// In system/fvSolution, increase maxIter:
"(U|e|Yi)"
{
    solver          PBiCGStab;
    preconditioner  DILU;
    tolerance       1e-10;
    relTol          0;
    maxIter         1000;   // increase from default
}
```

---

## Detonation Fails to Initiate

### Symptoms
- Shock wave forms but decays
- No sustained pressure wave after initial pulse

### Causes & fixes

| Cause | Fix |
|-------|-----|
| Driver pressure too low | Increase driver p (try 30-50x ambient) |
| Driver temperature too low | Increase to 1500-2500K |
| Driver region too small | Increase driver width (try 5-10mm) |
| Wrong mixture composition | Verify fuel/oxidizer ratio is detonable |
| Chemistry off | Check `chemistry on;` in chemistryProperties |
| Wrong inert species | Verify `inertSpecie` exists in species list and in `0/` directory |

---

## Wrong Detonation Speed

### Diagnosis
Measure shock position vs time from log output. Compare to CJ speed.

### Common causes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Speed too high | Over-driven by strong driver | Use weaker driver or wait longer for decay |
| Speed too low | Under-resolved mesh | Refine mesh in detonation region |
| Speed too low | Excessive numerical dissipation | Switch to HLLC, use vanLeer/ROUND limiters |
| Speed oscillates | CFL too high | Lower maxCo |
| Speed wrong by >5% | ODE tolerance too loose | Tighten absTol to 1e-8, relTol to 1e-4 |

---

## Build Errors

### "file not found" for fluxSchemes library
```
ld: cannot find -lfluxSchemes_improved
```
**Fix**: Build flux schemes first: `cd fluxSchemes_improved && wmake`

### "undefined reference to" DLBFoam symbols
**Fix**: Build DLBFoam first: `cd DLBFoam-1.0-1.0_OF8/src/thermophysicalModels/chemistryModel && wmake`

### General build order
Run `./Allwmake` from the solver root -- it handles dependencies in order.

---

## Runtime Library Load Failures

```
dlopen error: libchemistryModel_DLB.so: cannot open shared object file
```

### Fix
1. Check library was compiled: `ls $FOAM_USER_LIBBIN/libchemistryModel_DLB.so`
2. If missing, rebuild: `cd DLBFoam-1.0-1.0_OF8/... && wmake`
3. If not needed, comment out from `system/controlDict` libs list

---

## Memory Issues (Large Cases)

### Symptoms
- OOM killer terminates process
- Swap usage grows unbounded

### Fixes
| Strategy | How |
|----------|-----|
| Use parallel decomposition | More MPI ranks = less memory per rank |
| Reduce write frequency | Increase `writeInterval` |
| Enable `purgeWrite` | `purgeWrite 3;` keeps only last 3 time dirs |
| Reduce field output | Only write needed fields (use `writeObjects`) |
| Use binary output | `writeFormat binary;` (smaller files, faster I/O) |

---

## Slow Chemistry (Performance Bottleneck)

### Diagnosis
- Log shows most time in chemistry solve
- Unbalanced: some MPI ranks take much longer

### Fixes
| Strategy | How |
|----------|-----|
| Enable DLBFoam | `chemistryType { method loadBalanced; }` + load libs |
| Enable reference mapping | Fill `refmapping {}` block in chemistryProperties |
| Loosen tolerances | absTol 1e-6, relTol 1e-3 (check accuracy) |
| Use seulex solver | Generally best for stiff detonation chemistry |
| Reduce mechanism | Use a reduced mechanism with fewer species |

---

## Diagnostic Commands

```bash
# Check mesh quality
checkMesh

# Monitor residuals during run
grep "Solving for" log.detonationFoam | tail -20

# Check CFL number
grep "Courant" log.detonationFoam | tail -10

# Check mass conservation
grep "sum(rho)" log.detonationFoam | tail -5

# Check for negative species
grep "bounding" log.detonationFoam | head -20

# Check shock position
grep "SW_position" log.detonationFoam | tail -10

# Time per step
grep "ExecutionTime" log.detonationFoam | tail -5
```
