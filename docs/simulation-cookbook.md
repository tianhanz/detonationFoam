# detonationFoam Simulation Cookbook

Step-by-step workflows for common simulation tasks.

---

## Workflow 1: Run the Tutorial Case (First Simulation)

### Prerequisites
- OpenFOAM 8 sourced (`source /opt/openfoam8/etc/bashrc` or equivalent)
- **Note**: OF9 partially works (flux schemes & dynamic mesh compile, main solver fails due to header renames). Use OF8 or port.
- detonationFoam compiled (`cd applications/solvers/detonationFoam_V2.0 && bash Allwmake`)

### Steps
```bash
# 1. Copy tutorial to a working directory
cp -r tutorials/1D_NH3_O2_cracking_0.3_detonation $FOAM_RUN/my_first_case
cd $FOAM_RUN/my_first_case

# 2. Generate mesh
blockMesh

# 3. Set initial conditions (driver region)
setFields

# 4. Run the solver
detonationFoam_V2.0

# 5. Post-process (ParaView)
paraFoam
# Or: foamToVTK && open with ParaView
```

### What to check
- Pressure wave propagating from left to right
- Detonation speed should approach CJ value
- Temperature behind the wave should be ~2000-3000K
- Species profiles: fuel consumed, products formed behind wave

---

## Workflow 2: Parallel Run (MPI)

```bash
# 1. Set up decomposition
# Edit system/decomposeParDict:
#   numberOfSubdomains  4;
#   method simple;
#   simpleCoeffs { n (4 1 1); delta 0.001; }

# 2. Decompose
decomposePar

# 3. Run in parallel
mpirun -np 4 detonationFoam_V2.0 -parallel

# 4. Reconstruct for post-processing
reconstructPar
```

---

## Workflow 3: Switch Flux Scheme

Edit `system/fvSchemes`:
```
// Change from:
fluxScheme    Kurganov;
// To:
fluxScheme    HLLC;
```

No other changes needed. The flux scheme is runtime-selected.

**Comparison checklist:**
- [ ] Run both cases with identical mesh, ICs, and time step
- [ ] Compare shock position vs time
- [ ] Compare peak pressure profiles
- [ ] HLLC should give sharper shock fronts

---

## Workflow 4: Set Up a New Fuel System

### Required files to modify

1. **Reaction mechanism**: `constant/foam/reactions.foam`
   - Species list, reactions with Arrhenius parameters (A, beta, Ta)
   - Source: published mechanisms or Cantera conversion

2. **Species list**: `constant/foam/species.foam`
   - Must match reaction mechanism

3. **Thermodynamic data**: `constant/foam/thermo.foam`
   - JANAF polynomial coefficients for each species
   - Source: NASA Glenn thermodynamic database or Cantera

4. **Initial conditions** (`0/` directory):
   - Create a file for each species (copy Ydefault, set values)
   - Set correct mixture composition (mass fractions must sum to 1)
   - Set correct initial pressure and temperature

5. **Inert species**: `constant/thermophysicalProperties`
   - `inertSpecie` must be in species list and present in significant amount
   - Usually N2 or AR (diluent)

6. **Driver conditions**: `system/setFieldsDict`
   - CJ conditions from Cantera/SDToolbox or shock & detonation toolbox
   - Or simply high P + high T (e.g., 30*p0 and 2000K)

### Cantera helper (compute CJ conditions)
```python
import cantera as ct
# Use SDToolbox or similar to compute:
# - CJ detonation speed (D_CJ)
# - Post-detonation state (T_CJ, p_CJ)
# - These inform your driver conditions
```

---

## Workflow 5: Enable 2D Adaptive Mesh Refinement

### system/controlDict additions
```
libs
(
    "libdynamicMesh2D.so"
    "libdynamicFvMesh2D.so"
);
```

### constant/dynamicMeshDict
```
dynamicFvMesh   dynamicRefineFvMesh2D;

dynamicRefineFvMesh2DCoeffs
{
    refineInterval  1;          // Refine every N steps
    field           normalisedGradrho;  // Field to base refinement on
    lowerRefineLevel 0.1;       // Refine where field > this
    upperRefineLevel 1e6;       // Don't refine where field > this
    unrefineLevel   0.05;       // Unrefine where field < this
    nBufferLayers   2;          // Buffer layers around refined region
    maxRefinement   3;          // Max refinement levels
    maxCells        500000;     // Hard cell count limit
    correctFluxes   // Flux fields to correct after refinement
    (
        (phi none)
        (rhoPhi none)
        (rhoUPhi none)
        (rhoEPhi none)
    );
    dumpLevel       true;
}
```

---

## Workflow 6: Parameter Study (Batch Runs)

### Shell script template
```bash
#!/bin/bash
# Parameter study: vary driver pressure
BASE_CASE="tutorials/1D_NH3_O2_cracking_0.3_detonation"

for P_DRIVER in 5e6 7e6 9e6 12e6 15e6; do
    CASE_DIR="study_p${P_DRIVER}"
    cp -r $BASE_CASE $CASE_DIR
    cd $CASE_DIR

    # Modify driver pressure in setFieldsDict
    sed -i "s/volScalarFieldValue p .*/volScalarFieldValue p ${P_DRIVER};/" system/setFieldsDict

    # Run
    blockMesh
    setFields
    detonationFoam_V2.0 > log.detonationFoam 2>&1

    cd ..
done
```

### Monitoring a running case
```bash
# Watch residuals
tail -f log.detonationFoam | grep "^Time ="

# Check Courant number
grep "Courant Number" log.detonationFoam | tail -5

# Check if detonation initiated (shock position)
grep "SW_position" log.detonationFoam | tail -5
```

---

## Workflow 7: Post-Processing Checklist

### Essential checks for every detonation simulation
1. **Detonation speed**: measure shock position vs time, compute dx/dt
   - Should converge to CJ speed for self-sustained detonation
2. **Pressure profile**: peak pressure behind shock front
   - Von Neumann spike visible? (indicates ZND structure resolved)
3. **Temperature profile**: post-shock temperature
4. **Species profiles**: fuel consumption, product formation behind wave
5. **Max pressure field** (`pMax`): reveals detonation cell structure in 2D
6. **Density gradient** (`normalisedGradrho`): schlieren-like visualization

### Extract 1D data along a line
```bash
# Use OpenFOAM's sample utility
# system/sampleDict:
# type    sets;
# setFormat raw;
# sets ( centerline { type uniform; axis x; start (0 0 0); end (0.1 0 0); nPoints 1000; } );
# fields ( p T U );
postProcess -func sample -latestTime
```

---

## Workflow 8: Restart a Simulation

```bash
# 1. Find latest time directory
ls -d [0-9]* | sort -g | tail -1
# e.g., 0.000150

# 2. Edit system/controlDict
#    startFrom    latestTime;

# 3. Run again
detonationFoam_V2.0
```

For parallel restart:
```bash
# Decompose the latest time if needed
decomposePar -time 0.000150
mpirun -np 4 detonationFoam_V2.0 -parallel
```
