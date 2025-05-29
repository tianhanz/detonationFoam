detonationFoam_V2.0 based on OpenFOAM version 8 is released.
The author will gradually upload example cases and improve the corresponding documentation before the end of June 2025.
## What's new?
1. Optimized the code structure (A new dictionary file named ‘solverTypeProperties’ has been added under the constant directory of the case folder to select the solver type, replacing the approach in version 1.0 where three separate solvers were compiled).

3. Fixed an initialization error in the turbulence model.

4. Modified the selection strategy for reconstructed variable members in convective flux computation (showing improved performance in supersonic combustion ramjet simulations).

# detonationFoam: An open-source solver for simulation of gaseous detonation based on OpenFOAM

## Directory structure
detonationFoam_V2.0
   ```
   solverTypeEuler (Solve Euler equations)
   solverTypeNS_Sutherland (Solve N-S equations; transport parameters are calculated according to Sutherland model)
   solverTypeNS_mixtureAverage (Solve N-S equations; transport parameters are calculated according to mixture-averaged model)
   fluxSchemes_improved (Improved convective flux computation library)
   DLBFoam-1.0-1.0_OF8 (Dynamic load balance library: https://github.com/blttkgl/DLBFoam-1.0/tree/v1.0_OF8. Optional)
   dynamicMesh2D (2D adaptive mesh refinement library. Optional)
   ROUNDSchemes (Low-dissipation reconstruction scheme. Optional)
   ```
## Compiling 
1. Install OpenFOAM version 8

2. Compile detonationFoam_V2.0
   ```
   cd detonationFoam_V2.0
   ./Allwmake
   ```
## Applications
Since detonationFoam solver released on Github, it has been successfully applied in simulation of detonation, scramjet, reactive boundary layer. Here are some typical examples.

### Detonation reflection [Z. Yang, B. Zhang, H.D. Ng, Experimental observations of gaseous cellular detonation reflection, Proceedings of the Combustion Institute 40 (2024) 105519]
<img src="https://github.com/user-attachments/assets/ad47ad92-0bc0-47e9-ba89-baad03fc08a0" width="600"/>

### Detonation initiation [J. Sun, P. Yang, Y. Wang, Z. Chen, Numerical study on detonation initiation by multiple hot spots, Proceedings of the Combustion Institute 40 (2024) 105191]
<img src="https://github.com/user-attachments/assets/80dbdd81-5235-41cc-903b-6966e6d70cbb" width="600"/>


## Getting help and reporting bugs
Please submit a GitHub issue if you found a bug in the program. If you need help with the software or have further questions, contact sunjie_coe@pku.edu.cn and cz@pku.edu.cn.

##  Citation
If you use the code for your works and researches, please cite: 

   ```
   J. Sun, Y. Wang, B. Tian, Z. Chen, detonationFoam: An open-source solver for simulation of gaseous detonation based on OpenFOAM, Computer Physics Communications 292 (2023) 108859.
   ```
