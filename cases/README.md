# detonationFoam Production Cases

## 1D H2/O2 CJ Detonation (`1D_H2O2_detonation/`)

Classic 1D Chapman-Jouguet detonation benchmark using the Burke et al. (2011)
H2/O2 mechanism (10 species, 27 reactions).

| Parameter | Value |
|-----------|-------|
| Mixture | Stoichiometric H2/air (2H2 + O2 + 3.76N2) |
| Mechanism | Burke 2011 (Int. J. Chem. Kinet.) |
| Initial pressure | 1 atm (101,325 Pa) |
| Initial temperature | 300 K |
| Ignition | Hot spot at x < 5 mm: 30 atm, 2500 K |
| Domain | 0.2 m (20 cm), 40,000 cells, dx = 5 um |
| End time | 50 us |
| Flux scheme | HLLC |
| Solver type | Euler (inviscid) |
| Chemistry | DLB + seulex ODE |
| Expected CJ velocity | ~1968 m/s |
| Expected CJ pressure | ~15.6 atm |

**Expected runtime**: ~2-4 hours on 8 cores.

### Running locally
```bash
cd cases/1D_H2O2_detonation
blockMesh
setFields
decomposePar
mpirun -np 8 detonationFoam_V2.0 -parallel
reconstructPar
```

### Running on Bohrium
```bash
python bohrium/submit_detonation.py cases/1D_H2O2_detonation --np 8
```

---

## 2D H2/O2 Cellular Detonation (`2D_H2O2_cellular/`)

2D cellular detonation structure development. A planar detonation propagates
in a channel with periodic top/bottom boundaries, allowing transverse waves
to develop and form the characteristic cellular pattern (diamond-shaped cells
visible in maximum pressure tracks).

| Parameter | Value |
|-----------|-------|
| Mixture | Stoichiometric H2/air |
| Domain | 10 cm x 2 cm, 5000 x 1000 = 5M cells, dx = dy = 20 um |
| End time | 100 us |
| Boundaries | Periodic top/bottom, wall left/right |
| Perturbation | Asymmetric hot spot to seed transverse instabilities |
| Expected cell size | ~5-15 mm (weakly unstable regime) |

**Expected runtime**: ~12-24 hours on 32 cores.

### Running on Bohrium
```bash
python bohrium/submit_detonation.py cases/2D_H2O2_cellular \
    --np 32 --machine c32_m64_cpu --max-time 1440
```

---

## Mechanism: Burke et al. (2011)

The H2/O2 mechanism files in `constant/foam/` were converted from Chemkin
format using `bohrium/chemkin2foam.py`:

```bash
python bohrium/chemkin2foam.py \
    --chem ~/asurf/mechanisms/H2_Burke_2011_11sp/chem.inp \
    --therm ~/asurf/mechanisms/H2_Burke_2011_11sp/therm.dat \
    --tran ~/asurf/mechanisms/H2_Burke_2011_11sp/tran.dat \
    --output cases/1D_H2O2_detonation/constant/foam/
```

Reference: M.P. Burke, M. Chaos, Y. Ju, F.L. Dryer, S.J. Klippenstein,
"Comprehensive H2/O2 Kinetic Model for High-Pressure Combustion,"
Int. J. Chem. Kinet. (2011).
