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
    return Ts


def _collision_integral_mu(T_star):
    """Neufeld (1972) collision integral Omega(2,2)* for viscosity."""
    A, B, C, D = 1.16145, 0.14874, 0.52487, 0.77320
    E, F, G, H = 2.16178, 2.43787, -6.435e-4, 18.0323
    return A * T_star**(-B) + C * (-(D * T_star).real if isinstance(D * T_star, complex) else __import__('math').exp(-D * T_star)) + E * __import__('math').exp(-F * T_star)


def compute_transport_polys(mw, eps_k, sigma, Tlow=200, Thigh=6000):
    """Compute polynomial transport coefficients from Lennard-Jones parameters.

    Uses Chapman-Enskog theory to compute mu(T) and kappa(T) at sample points,
    then fits 4th-order polynomials in T and log(T).

    Returns (As, Ts, muCoeffs, muLogCoeffs, kappaCoeffs, kappaLogCoeffs).
    """
    import math
    import numpy as np

    kB = 1.380649e-23   # J/K
    NA = 6.02214076e23   # 1/mol
    R_gas = 8.314462     # J/(mol K)

    sigma_m = sigma * 1e-10  # Angstrom to meters
    m = mw * 1e-3 / NA       # kg per molecule

    # Sample temperatures
    temps = np.linspace(max(Tlow, 200), min(Thigh, 6000), 50)

    mu_vals = []
    kappa_vals = []

    for T in temps:
        T_star = T / max(eps_k, 1.0)

        # Neufeld collision integral Omega(2,2)*
        omega_22 = (1.16145 * T_star**(-0.14874)
                    + 0.52487 * math.exp(-0.77320 * T_star)
                    + 2.16178 * math.exp(-2.43787 * T_star))

        # Chapman-Enskog viscosity: mu = 5/16 * sqrt(pi * m * kB * T) / (pi * sigma^2 * Omega_22)
        mu = (5.0 / 16.0) * math.sqrt(math.pi * m * kB * T) / (math.pi * sigma_m**2 * omega_22)
        mu_vals.append(mu)

        # Eucken relation for thermal conductivity: kappa = mu * (Cv + 9/4 * R/M)
        # For monoatomic: Cv = 3/2 R/M, for diatomic: Cv = 5/2 R/M
        Cv = 2.5 * R_gas / (mw * 1e-3)  # J/(kg K), rough average
        kappa = mu * (Cv + 9.0 / 4.0 * R_gas / (mw * 1e-3))
        kappa_vals.append(kappa)

    mu_vals = np.array(mu_vals)
    kappa_vals = np.array(kappa_vals)

    # Sutherland fit: mu = As * sqrt(T) / (1 + Ts/T)
    Ts = 1.5 * eps_k
    # Fit As from least squares
    rhs = mu_vals * (1 + Ts / temps) / np.sqrt(temps)
    As = float(np.mean(rhs))

    # Polynomial fits (4 terms): f(T) = c0 + c1*T + c2*T^2 + c3*T^3
    # muCoeffs<8>: first 4 used, last 4 zero
    mu_poly = np.polyfit(temps, mu_vals, 3)[::-1]     # ascending order
    kappa_poly = np.polyfit(temps, kappa_vals, 3)[::-1]

    # Log fits: f(ln(T)) = c0 + c1*ln(T) + c2*ln(T)^2 + c3*ln(T)^3
    lnT = np.log(temps)
    mu_log_poly = np.polyfit(lnT, np.log(mu_vals), 3)[::-1]
    kappa_log_poly = np.polyfit(lnT, np.log(kappa_vals), 3)[::-1]

    return (As, Ts,
            list(mu_poly) + [0]*4,
            list(mu_log_poly) + [0]*4,
            list(kappa_poly) + [0]*4,
            list(kappa_log_poly) + [0]*4)


def write_species_foam(species_list, outdir):
    """Write species.foam in OpenFOAM format."""
    path = outdir / "species.foam"
    with open(path, "w") as f:
        f.write("species\n")
        f.write(f"{len(species_list)}\n(\n")
        for sp in species_list:
            f.write(f"{sp}\n")
        f.write(")\n;\n")
    print(f"  Wrote {path} ({len(species_list)} species)")


def _fmt_coeffs(vals):
    """Format a list of floats as inline OpenFOAM coefficients."""
    return "  ".join(f"{v}" for v in vals)


def write_thermo_foam(species_list, thermo, trans, outdir):
    """Write thermo.foam matching detonationFoam's expected format."""
    path = outdir / "thermo.foam"
    with open(path, "w") as f:
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
            sigma = tr.get("sigma", 3.0)

            # Compute transport properties
            try:
                As, Ts, muC, muLC, kapC, kapLC = compute_transport_polys(
                    mw, eps_k, sigma, Tlow, Thigh)
            except Exception as e:
                print(f"  WARNING: transport computation failed for {sp}: {e}")
                As, Ts = 1e-6, 150
                muC = muLC = kapC = kapLC = [0]*8

            f.write(f"{sp}\n{{\n")

            # specie block
            f.write(f"\tspecie\n\t{{\n")
            f.write(f"\t\tnMoles \t 1;\n")
            f.write(f"\t\tmolWeight \t{mw};\n")
            f.write(f"\t}}\n\n")

            # thermodynamics block (JANAF)
            low_str = "\t".join(f"{c}" for c in low)
            high_str = "\t".join(f"{c}" for c in high)
            f.write(f"\tthermodynamics\n\t{{\n")
            f.write(f"\t\tTlow\t\t{Tlow};\n")
            f.write(f"\t\tThigh\t\t{Thigh};\n")
            f.write(f"\t\tTcommon\t\t{Tcommon};\n")
            f.write(f"\t\tlowCpCoeffs\t(\t{low_str}  );\n")
            f.write(f"\t\thighCpCoeffs\t(\t{high_str}  );\n")
            f.write(f"\t}}\n\n")

            # transport block
            mu_str = "  ".join(f"{c}" for c in muC)
            muL_str = "  ".join(f"{c}" for c in muLC)
            kap_str = "  ".join(f"{c}" for c in kapC)
            kapL_str = "  ".join(f"{c}" for c in kapLC)
            f.write(f"\ttransport \n\t{{\n")
            f.write(f"\t\tAs\t{As:.15e};\n")
            f.write(f"\t\tTs\t{Ts:.15f};\n")
            f.write(f"\t\tmuLogCoeffs<8>\t(\t{muL_str}  );\n")
            f.write(f"\t\tmuCoeffs<8>\t(\t{mu_str}  );\n")
            f.write(f"\t\tkappaLogCoeffs<8>\t(\t{kapL_str}  );\n")
            f.write(f"\t\tkappaCoeffs<8>\t(\t{kap_str}  );\n")
            f.write(f"\t}}\n\n")

            # elements block
            f.write(f"\telements\n\t{{\n")
            for el, count in elems.items():
                f.write(f"\t\t{el}\t{count};\n")
            f.write(f"\t}}\n")

            f.write(f"}}\n\n")

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
        # Filter out commented reactions (those starting with !)
        active = [r for r in reactions if not r["equation"].startswith("!")]
        f.write("reactions\n{\n")

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

            f.write(f"    un-named-reaction-{idx}\n    {{\n")
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
                # coeffs: count followed by (species efficiency) pairs
                f.write(f"        coeffs\n{len(species_list)}\n(\n")
                for sp in species_list:
                    eff = rxn["third_body_effs"].get(sp, 1.0)
                    f.write(f"({sp} {eff})\n")
                f.write(f");\n")

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
                    Tss = tp[3] if len(tp) > 3 else 1e30
                    f.write(f"            Tss             {Tss};\n")
                    f.write(f"        }}\n")

                # thirdBodyEfficiencies with coeffs list
                f.write(f"        thirdBodyEfficiencies\n        {{\n")
                f.write(f"            coeffs\n{len(species_list)}\n(\n")
                for sp in species_list:
                    eff = rxn["third_body_effs"].get(sp, 1.0)
                    f.write(f"({sp} {eff})\n")
                f.write(f");\n")
                f.write(f"        }}\n")

            f.write(f"    }}\n")

        f.write("}\n")
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
