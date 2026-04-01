#!/usr/bin/env python3
"""Generate grid convergence study cases for Paper [2].

Creates 5 cases:
  1. uniform_dx40  — 40 μm uniform mesh (coarse)
  2. uniform_dx20  — 20 μm uniform mesh
  3. uniform_dx10  — 10 μm uniform mesh
  4. uniform_dx05  — 5 μm uniform mesh (finest, reference)
  5. amr_base40_L2 — base 40 μm + 2 AMR levels → effective 10 μm at front

All use 1D geometry:
  - Domain: 5 cm (0.05 m), end time 10 μs
  - Mixture: 2H2 + O2 + 3.76 N2 (stoich H2/air)
  - Driver: x < 5 mm, 30 atm, 2500 K
  - HLLC, Euler, Rosenbrock34

Convergence quantities:
  - CJ detonation velocity (shock tracking)
  - Peak pressure behind shock
  - ZND induction length (distance from shock to 50% peak T rise)
  - Pressure and temperature profiles at fixed time
"""

import os
import shutil
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent.parent / "case"

# Resolutions: name, dx(m), ncells, is_amr, amr_levels
CASES = [
    ("uniform_dx40", 40e-6, 1250, False, 0),
    ("uniform_dx20", 20e-6, 2500, False, 0),
    ("uniform_dx10", 10e-6, 5000, False, 0),
    ("uniform_dx05", 5e-6, 10000, False, 0),
    ("amr_base40_L2", 40e-6, 1250, True, 2),
]

DOMAIN_LENGTH = 0.05  # 5 cm
DOMAIN_HEIGHT = 0.005  # 5 mm (1 cell in y for 1D)
DOMAIN_DEPTH = 0.001

END_TIME = 10e-6  # 10 μs — enough for ~20 mm propagation
WRITE_INTERVAL = 0.5e-6  # write every 0.5 μs for fine shock tracking

# Mixture: stoichiometric H2/air
Y_H2 = 0.02852
Y_O2 = 0.2264
Y_N2 = 0.7451


def write_header(obj_name, cls="dictionary"):
    return f"""\
/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Website:  https://openfoam.org
    \\\\  /    A nd           | Version:  9
     \\\\/     M anipulation  |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {obj_name};
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""


def create_case(name, dx, ncells, is_amr, amr_levels):
    cdir = CASE_DIR / name
    if cdir.exists():
        shutil.rmtree(cdir)

    # Create directory structure
    for d in ["0", "constant", "constant/foam", "system"]:
        (cdir / d).mkdir(parents=True, exist_ok=True)

    # === system/blockMeshDict ===
    eff_dx = dx / (2 ** amr_levels) if is_amr else dx
    if is_amr:
        mesh_comment = f"AMR {amr_levels} levels -> effective {eff_dx*1e6:.0f} um"
    else:
        mesh_comment = "Uniform mesh"
    (cdir / "system" / "blockMeshDict").write_text(
        write_header("blockMeshDict")
        + f"""\
// Grid convergence: {name}
// Domain: {DOMAIN_LENGTH} m, {ncells} cells, dx = {dx*1e6:.0f} um
// {mesh_comment}

convertToMeters 1;

vertices
(
    (0.0    0.0    -{DOMAIN_DEPTH})
    ({DOMAIN_LENGTH}  0.0    -{DOMAIN_DEPTH})
    ({DOMAIN_LENGTH}  {DOMAIN_HEIGHT}  -{DOMAIN_DEPTH})
    (0.0    {DOMAIN_HEIGHT}  -{DOMAIN_DEPTH})
    (0.0    0.0     {DOMAIN_DEPTH})
    ({DOMAIN_LENGTH}  0.0     {DOMAIN_DEPTH})
    ({DOMAIN_LENGTH}  {DOMAIN_HEIGHT}   {DOMAIN_DEPTH})
    (0.0    {DOMAIN_HEIGHT}   {DOMAIN_DEPTH})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({ncells} 1 1) simpleGrading (1 1 1)
);

edges ();

boundary
(
    inlet
    {{
        type wall;
        faces ( (0 4 7 3) );
    }}
    outlet
    {{
        type wall;
        faces ( (1 2 6 5) );
    }}
    bottom
    {{
        type wall;
        faces ( (0 1 5 4) );
    }}
    top
    {{
        type wall;
        faces ( (3 7 6 2) );
    }}
    frontAndBack
    {{
        type empty;
        faces ( (4 5 6 7) (0 3 2 1) );
    }}
);

mergePatchPairs ();

// ************************************************************************* //
"""
    )

    # === system/controlDict ===
    libs_block = ""
    if is_amr:
        libs_block = """libs
(
  "libdynamicMesh2D.so"
  "libdynamicFvMesh2D.so"
);
"""

    (cdir / "system" / "controlDict").write_text(
        write_header("controlDict")
        + f"""\
{libs_block}
application     detonationFoam_V2.0;

startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {END_TIME};

deltaT          1e-11;

writeControl    adjustableRunTime;
writeInterval   {WRITE_INTERVAL};
purgeWrite      0;
writeFormat     ascii;
writePrecision  12;
writeCompression off;
timeFormat      general;
timePrecision   12;
runTimeModifiable true;
adjustTimeStep  yes;
useAcousticCourant yes;
maxCo           0.1;
maxDeltaT       1e-6;
maxAcousticCo   0.1;

functions {{}}

// ************************************************************************* //
"""
    )

    # === system/fvSchemes ===
    (cdir / "system" / "fvSchemes").write_text(
        write_header("fvSchemes")
        + """\
fluxScheme      HLLC;

ddtSchemes
{
    default         Euler;
}

gradSchemes
{
    default         cellLimited Gauss linear 0.7;
}

divSchemes
{
    default        Gauss linear;
    div(rhoPhi,Yi_h)  Gauss limitedLinear 1;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default             linear;
    reconstruct(rho)    Minmod;
    reconstruct(rhoU)   MinmodV;
    reconstruct(rPsi)   Minmod;
    reconstruct(e)      Minmod;
    reconstruct(c)      Minmod;
}

snGradSchemes
{
    default         corrected;
}

// ************************************************************************* //
"""
    )

    # === system/fvSolution ===
    (cdir / "system" / "fvSolution").write_text(
        write_header("fvSolution")
        + """\
solvers
{
    "(rho|rhoU|rhoE)"
    {
        solver          diagonal;
    }
    "(rho|rhoU|rhoE)Final"
    {
        solver          diagonal;
    }
    "(U|e)"
    {
        solver          PBiCGStab;
        preconditioner  DIC;
        tolerance       1e-12;
        relTol          0.1;
    }
    "(U|e)Final"
    {
        $U;
        relTol          0;
    }
    "(Yi)"
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-12;
        relTol          0;
    }
}

CENTRAL
{
}

// ************************************************************************* //
"""
    )

    # === system/setFieldsDict ===
    (cdir / "system" / "setFieldsDict").write_text(
        write_header("setFieldsDict")
        + """\
defaultFieldValues
(
    volScalarFieldValue p 101325
    volScalarFieldValue T 300
);

regions
(
    boxToCell
    {
        box     (-1 -1 -1) (0.005 1 1);
        fieldValues
        (
            volScalarFieldValue p 3039750
            volScalarFieldValue T 2500
        );
    }
);

// ************************************************************************* //
"""
    )

    # === system/decomposeParDict ===
    (cdir / "system" / "decomposeParDict").write_text(
        write_header("decomposeParDict")
        + """\
numberOfSubdomains  4;

method          scotch;

// ************************************************************************* //
"""
    )

    # === constant/solverTypeProperties ===
    (cdir / "constant" / "solverTypeProperties").write_text(
        write_header("solverTypeProperties")
        + """\
solverType      Euler;

// ************************************************************************* //
"""
    )

    # === constant/thermophysicalProperties ===
    (cdir / "constant" / "thermophysicalProperties").write_text(
        write_header("thermophysicalProperties")
        + """\
thermoType
{
    type            hePsiThermo;
    mixture         multiComponentMixture;
    transport       sutherland;
    thermo          janaf;
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleInternalEnergy;
}

inertSpecie     N2;

#include "foam/species.foam"
#include "foam/thermo.foam"

// ************************************************************************* //
"""
    )

    # === constant/chemistryProperties ===
    (cdir / "constant" / "chemistryProperties").write_text(
        write_header("chemistryProperties")
        + """\
chemistryType
{
    solver          ode;
    method          standard;
}

chemistry       on;

initialChemicalTimeStep 1e-7;

odeCoeffs
{
    solver          Rosenbrock34;
    absTol          1e-10;
    relTol          1e-6;
}

#include "$FOAM_CASE/constant/foam/reactions.foam"

// ************************************************************************* //
"""
    )

    # === constant/combustionProperties ===
    (cdir / "constant" / "combustionProperties").write_text(
        write_header("combustionProperties")
        + """\
combustionModel laminar;

// ************************************************************************* //
"""
    )

    # === constant/momentumTransport ===
    (cdir / "constant" / "momentumTransport").write_text(
        write_header("momentumTransport")
        + """\
simulationType  laminar;

// ************************************************************************* //
"""
    )

    # === constant/foam/ — copy from existing 1D case ===
    foam_src = Path(__file__).resolve().parent.parent.parent.parent / "cases" / "1D_H2O2_detonation" / "constant" / "foam"
    for f in ["reactions.foam", "species.foam", "thermo.foam"]:
        src = foam_src / f
        if src.exists():
            shutil.copy2(src, cdir / "constant" / "foam" / f)
        else:
            print(f"  WARNING: {src} not found — copy manually from 1D case")

    # === 0/ field files ===
    for field, value, dim in [
        ("p", "101325", "[1 -1 -2 0 0 0 0]"),
        ("T", "300", "[0 0 0 1 0 0 0]"),
    ]:
        (cdir / "0" / field).write_text(
            write_header(field, cls="volScalarField")
            + f"""\
dimensions      {dim};

internalField   uniform {value};

boundaryField
{{
    "(inlet|outlet|top|bottom)"
    {{
        type            zeroGradient;
    }}
    frontAndBack
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
"""
        )

    # Velocity
    (cdir / "0" / "U").write_text(
        write_header("U", cls="volVectorField")
        + """\
dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{
    "(inlet|outlet|top|bottom)"
    {
        type            zeroGradient;
    }
    frontAndBack
    {
        type            empty;
    }
}

// ************************************************************************* //
"""
    )

    # Species fields
    for species, value in [("H2", str(Y_H2)), ("O2", str(Y_O2)), ("N2", str(Y_N2))]:
        (cdir / "0" / species).write_text(
            write_header(species, cls="volScalarField")
            + f"""\
dimensions      [0 0 0 0 0 0 0];

internalField   uniform {value};

boundaryField
{{
    "(inlet|outlet|top|bottom)"
    {{
        type            zeroGradient;
    }}
    frontAndBack
    {{
        type            empty;
    }}
}}

// ************************************************************************* //
"""
        )

    # Default species (Ydefault = 0)
    (cdir / "0" / "Ydefault").write_text(
        write_header("Ydefault", cls="volScalarField")
        + """\
dimensions      [0 0 0 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    "(inlet|outlet|top|bottom)"
    {
        type            zeroGradient;
    }
    frontAndBack
    {
        type            empty;
    }
}

// ************************************************************************* //
"""
    )

    # === AMR: constant/dynamicMeshDict ===
    if is_amr:
        (cdir / "constant" / "dynamicMeshDict").write_text(
            write_header("dynamicMeshDict")
            + f"""\
dynamicFvMesh   dynamicRefineFvMesh2D;

dynamicRefineFvMesh2DCoeffs
{{
    refineInterval      1;
    field               magGradrho;
    lowerRefineLevel    500;
    upperRefineLevel    1e10;
    unrefineLevel       100;
    maxRefinement       {amr_levels};
    maxCells            200000;
    nBufferLayers       2;
    nBufferLayersR      2;
    axis                2;
    axisVal             0;
    dumpLevel           true;

    correctFluxes
    (
        (phi none)
        (rhoPhi none)
        (rhoUPhi none)
        (rhoEPhi none)
    );
}}

// ************************************************************************* //
"""
        )

    if is_amr:
        amr_info = f", AMR L{amr_levels} -> eff {eff_dx*1e6:.0f}um"
    else:
        amr_info = ""
    print(f"  Created: {name} ({ncells} cells, dx={dx*1e6:.0f}um{amr_info})")


def main():
    print("=" * 60)
    print("Grid Convergence Study — Paper [2] (Sun 2023 CPC)")
    print("=" * 60)
    print(f"\nDomain: {DOMAIN_LENGTH*100:.0f} cm, endTime: {END_TIME*1e6:.0f} μs")
    print(f"Mixture: stoich H2/air, T0=300K, P0=1atm")
    print(f"Driver: x<5mm, 30atm, 2500K")
    print(f"Write interval: {WRITE_INTERVAL*1e6:.1f} μs\n")

    CASE_DIR.mkdir(parents=True, exist_ok=True)

    for name, dx, ncells, is_amr, levels in CASES:
        create_case(name, dx, ncells, is_amr, levels)

    print(f"\nAll cases created in: {CASE_DIR}")
    print("\nResolution summary:")
    print(f"  {'Case':<20s} {'dx(μm)':>8s} {'Cells':>8s} {'AMR':>5s} {'Eff dx(μm)':>10s}")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*5} {'-'*10}")
    for name, dx, ncells, is_amr, levels in CASES:
        eff = dx / (2 ** levels) if is_amr else dx
        amr_str = f"L{levels}" if is_amr else "—"
        print(f"  {name:<20s} {dx*1e6:>8.0f} {ncells:>8d} {amr_str:>5s} {eff*1e6:>10.0f}")


if __name__ == "__main__":
    main()
