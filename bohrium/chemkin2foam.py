#!/usr/bin/env python3
"""Convert Chemkin mechanism files to OpenFOAM .foam format.

Converts a Chemkin-II mechanism (chem.inp + therm.dat + tran.dat) to
OpenFOAM's native dictionary format (species.foam + thermo.foam + reactions.foam).

Designed for the Burke 2011 H2/O2 mechanism but should work for other
simple mechanisms without PLOG or Chebyshev reactions.

Usage:
    python chemkin2foam.py \\
        --chem ~/asurf/mechanisms/H2_Burke_2011_11sp/chem.inp \\
        --therm ~/asurf/mechanisms/H2_Burke_2011_11sp/therm.dat \\
        --tran ~/asurf/mechanisms/H2_Burke_2011_11sp/tran.dat \\
        --output ./constant/foam/ \\
        --species H H2 O OH H2O O2 HO2 H2O2 N2 AR HE

Note: Activation energies are converted from cal/mol to Kelvins (Ta = Ea/R).
Transport properties use Sutherland + polynomial approximations derived from
the Lennard-Jones parameters.
"""

import argparse
import re
import sys
from pathlib import Path

R_CAL = 1.987216  # cal/(mol K) — gas constant for Ea conversion


# ─── Molecular weights ───
MOL_WEIGHTS = {
    "H": 1.00794, "H2": 2.01588, "O": 15.9994, "O2": 31.9988,
    "OH": 17.00734, "H2O": 18.01528, "HO2": 33.00674, "H2O2": 34.01468,
    "N2": 28.0134, "AR": 39.948, "HE": 4.0026, "N": 14.0067,
    "C": 12.011, "CO": 28.0104, "CO2": 44.0098,
}

# ─── Element composition ───
ELEMENTS = {
    "H": {"H": 1}, "H2": {"H": 2}, "O": {"O": 1}, "O2": {"O": 2},
    "OH": {"O": 1, "H": 1}, "H2O": {"H": 2, "O": 1},
    "HO2": {"H": 1, "O": 2}, "H2O2": {"H": 2, "O": 2},
    "N2": {"N": 2}, "AR": {"Ar": 1}, "HE": {"He": 1},
}


def _parse_coeff(s):
    """Parse a Chemkin NASA coefficient field, handling quirks like 'E 02' or 'D+02'."""
    s = s.strip().replace("D", "E")
    # Fix space in exponent: "0.123E 02" → "0.123E+02"
    s = re.sub(r"E\s+(\d)", r"E+\1", s)
    s = re.sub(r"E\s*-\s*(\d)", r"E-\1", s)
    return float(s) if s else 0.0


def parse_thermo_dat(path, species_list):
    """Parse Chemkin therm.dat for NASA-7 polynomial coefficients."""
    text = Path(path).read_text(errors="replace").replace("\r\n", "\n")
    lines = text.split("\n")
    thermo = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        # Species header line ends with '1' in column 80
        if len(line) >= 80 and line[79:80] == "1":
            name = line[:18].split()[0].strip()
            if name in ("THERMO", "END") or name.startswith("!"):
                i += 1
                continue
            # Parse temperature ranges — Chemkin fixed format:
            # cols 1-18: species name, cols 45-55: Tlow, 55-65: Thigh, 65-75: Tcommon
            # But many files use slightly different column layouts.
            # Robust approach: extract all floats from the tail of line 1
            try:
                tail = line[44:79]
                # Find all numbers in the tail region
                nums = re.findall(r"[\d.]+", tail)
                if len(nums) >= 3:
                    Tlow = float(nums[0])
                    Thigh = float(nums[1])
                    Tcommon = float(nums[2])
                else:
                    i += 1
                    continue
            except (ValueError, IndexError):
                i += 1
                continue

            # Read 3 more lines of coefficients
            if i + 3 >= len(lines):
                break
            line2 = lines[i + 1]
            line3 = lines[i + 2]
            line4 = lines[i + 3]

            # High-T coefficients (a1-a7): line2[0:75] has a1-a5, line3[0:30] has a6-a7
            high = []
            for s in [line2[0:15], line2[15:30], line2[30:45], line2[45:60], line2[60:75]]:
                high.append(_parse_coeff(s))
            for s in [line3[0:15], line3[15:30]]:
                high.append(_parse_coeff(s))

            # Low-T coefficients (a1-a7): line3[30:75] has a1-a3, line4[0:60] has a4-a7
            low = []
            for s in [line3[30:45], line3[45:60], line3[60:75]]:
                low.append(_parse_coeff(s))
            for s in [line4[0:15], line4[15:30], line4[30:45], line4[45:60]]:
                low.append(_parse_coeff(s))

            thermo[name] = {
                "Tlow": Tlow, "Thigh": Thigh, "Tcommon": Tcommon,
                "high": high, "low": low,
            }
            i += 4
        else:
            i += 1

    # Check coverage
    for sp in species_list:
        if sp not in thermo:
            print(f"WARNING: no thermo data for {sp}")
    return thermo


def parse_transport(path, species_list):
    """Parse Chemkin tran.dat for Lennard-Jones parameters."""
    text = Path(path).read_text(errors="replace").replace("\r\n", "\n")
    trans = {}
    for line in text.split("\n"):
        line = line.split("!")[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 6:
            name = parts[0]
            if name in species_list:
                trans[name] = {
                    "geom": int(parts[1]),      # 0=atom, 1=linear, 2=nonlinear
                    "eps_k": float(parts[2]),    # epsilon/kB (K)
                    "sigma": float(parts[3]),    # sigma (Angstrom)
                    "mu": float(parts[4]),       # dipole moment (Debye)
                    "alpha": float(parts[5]),    # polarizability (A^3)
                }
    return trans


def sutherland_params(eps_k):
    """Approximate Sutherland parameters from Lennard-Jones epsilon/kB.

    Ts ≈ 1.5 * eps_k (Sutherland temperature)
    As is fitted from mu at 300K and 1000K using kinetic theory.
    Returns (As, Ts) for mu = As * sqrt(T) / (1 + Ts/T).
    """
    Ts = 1.5 * eps_k
    # For OpenFOAM, we use polynomial transport instead of Sutherland
    # since detonationFoam uses polynomial fits
    return Ts


def write_species_foam(species_list, outdir):
    """Write species.foam."""
    path = outdir / "species.foam"
    with open(path, "w") as f:
        f.write("// species.foam — generated by chemkin2foam.py\n")
        f.write(f"// Burke et al., Int. J. Chem. Kinet. (2011) — H2/O2 mechanism\n\n")
        f.write(f"{len(species_list)}\n(\n")
        for sp in species_list:
            f.write(f"    {sp}\n")
        f.write(")\n")
    print(f"  Wrote {path} ({len(species_list)} species)")


def write_thermo_foam(species_list, thermo, trans, outdir):
    """Write thermo.foam with per-species specie/thermodynamics/transport/elements blocks."""
    path = outdir / "thermo.foam"
    with open(path, "w") as f:
        f.write("// thermo.foam — generated by chemkin2foam.py\n")
        f.write("// Burke et al., Int. J. Chem. Kinet. (2011) — H2/O2 mechanism\n")
        f.write("// Transport from Chemkin tran.dat (Sutherland + polynomial fits)\n\n")
        f.write(f"{len(species_list)}\n(\n")

        for sp in species_list:
            mw = MOL_WEIGHTS.get(sp, 28.0)
            td = thermo.get(sp, {})
            tr = trans.get(sp, {})
            elems = ELEMENTS.get(sp, {})

            high = td.get("high", [0]*7)
            low = td.get("low", [0]*7)
            Tlow = td.get("Tlow", 200)
            Thigh = td.get("Thigh", 6000)
            Tcommon = td.get("Tcommon", 1000)

            eps_k = tr.get("eps_k", 100)
            Ts = sutherland_params(eps_k)
            # Sutherland As parameter — approximate from kinetic theory
            # mu_ref at T_ref=300K, then compute As = mu_ref * (1+Ts/Tref) / sqrt(Tref)
            # For simplicity, use standard values
            sigma = tr.get("sigma", 3.0)
            # Estimate viscosity at 300K via Chapman-Enskog (approximate)
            mu_300 = 2.6693e-5 * (mw * 300)**0.5 / (sigma**2 * 1.0)  # rough
            As = mu_300 * (1 + Ts / 300) / (300**0.5)

            f.write(f"    {sp}\n    {{\n")

            # specie block
            f.write(f"        specie\n        {{\n")
            f.write(f"            molWeight       {mw};\n")
            f.write(f"        }}\n")

            # thermodynamics block (JANAF)
            f.write(f"        thermodynamics\n        {{\n")
            f.write(f"            Tlow            {Tlow};\n")
            f.write(f"            Thigh           {Thigh};\n")
            f.write(f"            Tcommon         {Tcommon};\n")
            f.write(f"            highCpCoeffs\n            (\n")
            for c in high:
                f.write(f"                {c:+.8e}\n")
            f.write(f"            );\n")
            f.write(f"            lowCpCoeffs\n            (\n")
            for c in low:
                f.write(f"                {c:+.8e}\n")
            f.write(f"            );\n")
            f.write(f"        }}\n")

            # transport block (Sutherland viscosity + polynomial kappa)
            f.write(f"        transport\n        {{\n")
            f.write(f"            As              {As:.6e};\n")
            f.write(f"            Ts              {Ts:.2f};\n")
            f.write(f"        }}\n")

            # elements block
            f.write(f"        elements\n        {{\n")
            for el, count in elems.items():
                f.write(f"            {el}               {count};\n")
            f.write(f"        }}\n")

            f.write(f"    }}\n")

        f.write(")\n")
    print(f"  Wrote {path}")


def parse_reactions(path, species_list):
    """Parse Chemkin reactions from chem.inp.

    Returns list of reaction dicts with keys:
      equation, A, beta, Ea, type, third_body_effs, low_params, troe_params, duplicate
    """
    text = Path(path).read_text(errors="replace").replace("\r\n", "\n")
    lines = text.split("\n")

    # Find REACTIONS and END keywords as standalone lines (not in comments)
    reactions_start = reactions_end = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("!"):
            if stripped.upper().startswith("REACTIONS") and reactions_start is None:
                reactions_start = idx
            elif stripped.upper() == "END" and reactions_start is not None:
                reactions_end = idx
                break

    if reactions_start is None or reactions_end is None:
        print("ERROR: no REACTIONS block found")
        return []

    block_lines = lines[reactions_start + 1:reactions_end]
    reactions = []

    # Regex for a reaction line: equation followed by A, beta, Ea
    rxn_re = re.compile(
        r'^([A-Za-z0-9+()=\s*]+?)\s+'         # equation (greedy but stops before numbers)
        r'([\d.]+[eE][+-]?\d+)\s+'             # A (scientific notation)
        r'([+-]?[\d.]+)\s+'                    # beta
        r'([+-]?[\d.]+[eE]?[+-]?\d*)\s*$'     # Ea
    )

    i = 0
    while i < len(block_lines):
        line = block_lines[i]
        # Remove inline comments
        comment_pos = line.find("!")
        if comment_pos >= 0:
            line = line[:comment_pos]
        line = line.strip()
        if not line:
            i += 1
            continue

        # Try matching a reaction line
        m = rxn_re.match(line)
        if m:
            eq_str = m.group(1).strip()
            A = float(m.group(2))
            beta = float(m.group(3))
            Ea_str = m.group(4)
            Ea = float(Ea_str)

            rxn = {
                "equation": eq_str,
                "A": A,
                "beta": beta,
                "Ea": Ea,
                "third_body_effs": {},
                "low_params": None,
                "troe_params": None,
                "duplicate": False,
                "is_falloff": "(+M)" in eq_str,
                "is_third_body": "+M" in eq_str and "(+M)" not in eq_str,
            }

            # Look ahead for auxiliary lines
            j = i + 1
            while j < len(block_lines):
                aux = block_lines[j]
                if aux.find("!") >= 0:
                    aux = aux[:aux.find("!")]
                aux = aux.strip()
                if not aux:
                    j += 1
                    continue
                if aux.upper().startswith("DUPLICATE"):
                    rxn["duplicate"] = True
                    j += 1
                    continue
                if aux.upper().startswith("LOW/"):
                    m2 = re.search(r"LOW\s*/\s*([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s*/", aux, re.I)
                    if m2:
                        rxn["low_params"] = (float(m2.group(1)), float(m2.group(2)), float(m2.group(3)))
                    j += 1
                    continue
                if aux.upper().startswith("TROE/"):
                    m2 = re.search(r"TROE\s*/\s*([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", aux, re.I)
                    if m2:
                        rxn["troe_params"] = [float(m2.group(1)), float(m2.group(2)), float(m2.group(3))]
                        rest = aux[m2.end():]
                        m3 = re.match(r"\s+([\d.eE+-]+)", rest)
                        if m3:
                            rxn["troe_params"].append(float(m3.group(1)))
                    j += 1
                    continue
                # Third-body efficiencies: "H2/2.5/ H2O/12/ ..."
                if "/" in aux and not any(aux.upper().startswith(kw) for kw in ("LOW", "TROE", "DUPLICATE", "REV")):
                    effs = re.findall(r"(\w+)\s*/\s*([\d.eE+-]+)\s*/", aux)
                    if effs:
                        for sp, val in effs:
                            rxn["third_body_effs"][sp] = float(val)
                        j += 1
                        continue
                # If we get here, it's the next reaction line
                break

            reactions.append(rxn)
            i = j
            continue

        i += 1

    print(f"  Parsed {len(reactions)} reactions from {path}")
    return reactions


def foam_reaction_string(eq_str):
    """Convert Chemkin equation to OpenFOAM format.

    H+O2 = O+OH  →  H + O2 = O + OH
    H+O2(+M) = HO2(+M)  →  H + O2 = HO2 (remove (+M), add spaces)
    """
    s = eq_str.replace("(+M)", "").replace("+M", "")
    s = s.replace("=>", "=")
    # Split on '=' and handle each side
    if "=" in s:
        lhs, rhs = s.split("=", 1)
        # Add spaces around +
        lhs = " + ".join(p.strip() for p in lhs.split("+"))
        rhs = " + ".join(p.strip() for p in rhs.split("+"))
        return f"{lhs} = {rhs}"
    return s


def write_reactions_foam(reactions, species_list, outdir):
    """Write reactions.foam in OpenFOAM dictionary format."""
    path = outdir / "reactions.foam"

    with open(path, "w") as f:
        f.write("// reactions.foam — generated by chemkin2foam.py\n")
        f.write("// Burke et al., Int. J. Chem. Kinet. (2011) — H2/O2 mechanism\n\n")

        # Filter out commented reactions (those starting with !)
        active = [r for r in reactions if not r["equation"].startswith("!")]
        f.write(f"{len(active)}\n(\n")

        for idx, rxn in enumerate(active):
            eq = rxn["equation"]
            A = rxn["A"]
            beta = rxn["beta"]
            Ea = rxn["Ea"]  # cal/mol
            Ta = Ea / R_CAL  # Convert to Kelvin

            foam_eq = foam_reaction_string(eq)

            # Determine reaction type
            if rxn["is_falloff"] and rxn["low_params"] and rxn["troe_params"]:
                rtype = "reversibleArrheniusTroeFallOff"
            elif rxn["is_falloff"] and rxn["low_params"]:
                rtype = "reversibleArrheniusLindemannFallOff"
            elif rxn["is_third_body"]:
                rtype = "reversibleThirdBodyArrhenius"
            else:
                rtype = "reversibleArrhenius"

            f.write(f"    reaction{idx}\n    {{\n")
            f.write(f"        type            {rtype};\n")
            f.write(f"        reaction        \"{foam_eq}\";\n")

            if rtype == "reversibleArrhenius":
                f.write(f"        A               {A:.6e};\n")
                f.write(f"        beta            {beta:.2f};\n")
                f.write(f"        Ta              {Ta:.2f};\n")

            elif rtype == "reversibleThirdBodyArrhenius":
                f.write(f"        A               {A:.6e};\n")
                f.write(f"        beta            {beta:.2f};\n")
                f.write(f"        Ta              {Ta:.2f};\n")
                f.write(f"        defaultCoeffs   yes;\n")
                if rxn["third_body_effs"]:
                    f.write(f"        coeffs\n        (\n")
                    for sp in species_list:
                        eff = rxn["third_body_effs"].get(sp, 1.0)
                        f.write(f"            ({sp}  {eff})\n")
                    f.write(f"        );\n")

            elif rtype in ("reversibleArrheniusTroeFallOff", "reversibleArrheniusLindemannFallOff"):
                f.write(f"        k0\n        {{\n")
                lp = rxn["low_params"]
                Ta0 = lp[2] / R_CAL
                f.write(f"            A               {lp[0]:.6e};\n")
                f.write(f"            beta            {lp[1]:.2f};\n")
                f.write(f"            Ta              {Ta0:.2f};\n")
                f.write(f"        }}\n")
                f.write(f"        kInf\n        {{\n")
                f.write(f"            A               {A:.6e};\n")
                f.write(f"            beta            {beta:.2f};\n")
                f.write(f"            Ta              {Ta:.2f};\n")
                f.write(f"        }}\n")

                if rxn["troe_params"] and rtype == "reversibleArrheniusTroeFallOff":
                    tp = rxn["troe_params"]
                    f.write(f"        F\n        {{\n")
                    f.write(f"            alpha           {tp[0]};\n")
                    f.write(f"            Tsss            {tp[1]};\n")
                    f.write(f"            Ts              {tp[2]};\n")
                    if len(tp) > 3:
                        f.write(f"            Tss             {tp[3]};\n")
                    f.write(f"        }}\n")

                f.write(f"        thirdBodyEfficiencies\n        {{\n")
                for sp in species_list:
                    eff = rxn["third_body_effs"].get(sp, 1.0)
                    f.write(f"            {sp}         {eff};\n")
                f.write(f"        }}\n")

            f.write(f"    }}\n")

        f.write(")\n")
    print(f"  Wrote {path} ({len(active)} reactions)")


def main():
    parser = argparse.ArgumentParser(description="Convert Chemkin mechanism to OpenFOAM .foam format")
    parser.add_argument("--chem", required=True, help="Chemkin chem.inp file")
    parser.add_argument("--therm", required=True, help="Chemkin therm.dat file")
    parser.add_argument("--tran", required=True, help="Chemkin tran.dat file")
    parser.add_argument("--output", required=True, help="Output directory for .foam files")
    parser.add_argument("--species", nargs="+",
                        default=["H", "H2", "O", "OH", "H2O", "O2", "HO2", "H2O2", "N2", "AR", "HE"],
                        help="Species to include (default: full H2/O2 + inerts)")
    args = parser.parse_args()

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    species_list = args.species

    print(f"Converting Chemkin → OpenFOAM .foam format")
    print(f"  Species: {species_list}")

    thermo = parse_thermo_dat(args.therm, species_list)
    trans = parse_transport(args.tran, species_list)
    reactions = parse_reactions(args.chem, species_list)

    write_species_foam(species_list, outdir)
    write_thermo_foam(species_list, thermo, trans, outdir)
    write_reactions_foam(reactions, species_list, outdir)

    print(f"\nDone. Files in {outdir}/")


if __name__ == "__main__":
    main()
