#!/usr/bin/env python3
"""Phase 2: Compute independent CJ reference for Paper [2] validation.

Uses the standard method: CJ velocity = minimum detonation velocity on
the equilibrium Hugoniot. Implemented via density-ratio sweep.

Reference: Sun et al., CPC 292 (2023) 108859
Mixture: 2H2 + O2 + 3.76N2, T0=300K, P0=1atm
"""

import cantera as ct
import numpy as np
import json
from pathlib import Path

T0 = 300.0
P0 = ct.one_atm
COMP = "H2:2, O2:1, N2:3.76"


def compute_cj(mech="h2o2.yaml"):
    """Compute CJ detonation velocity and post-CJ state.

    Method: sweep over density ratio rho2/rho1, for each compute the
    Hugoniot pressure and enthalpy, find equilibrium, then compute
    detonation velocity D. The CJ point minimizes D.
    """
    gas1 = ct.Solution(mech)
    gas1.TPX = T0, P0, COMP
    rho1 = gas1.density
    h1 = gas1.enthalpy_mass
    v1 = 1.0 / rho1

    gas2 = ct.Solution(mech)

    # Sweep compression ratio eta = rho2/rho1 = v1/v2
    # For CJ detonation, typical eta ~ 1.7-1.8 for H2/air
    # Search range covers weak to strong detonation
    etas = np.linspace(1.3, 3.0, 500)
    D_vals = []
    valid_etas = []

    for eta in etas:
        v2 = v1 / eta
        rho2 = rho1 * eta

        # Rayleigh line: P2 - P1 = rho1^2 * D^2 * (v1 - v2)
        # Hugoniot: h2 - h1 = 0.5 * (P2 + P1) * (v1 - v2)
        # => h2 = h1 + 0.5 * (P2 + P1) * (v1 - v2)
        # We need to find P2 from equilibrium at (h2, rho2)

        # Use iterative approach: guess P2, compute h2 from Hugoniot,
        # equilibrate at (h2, P2), check if density matches rho2
        # Simpler: equilibrate at (v2, s) or (v2, h_hugoniot)

        # Alternative: from Hugoniot relation only:
        # P2 = P1 + rho1 * D^2 * (1 - 1/eta)
        # h2 = h1 + 0.5 * (P2 + P1) * (v1 - v2) = h1 + 0.5*(P2+P1)*v1*(1 - 1/eta)
        # These two plus equilibrium at (h2, P2) give us the system.
        # But D is unknown. Instead, use the energy Hugoniot:
        # h2 = h1 + 0.5*(P2 + P1)*(v1 - v2)
        # and equilibrium at (rho2, h2) ... but we need another relation.

        # Better approach: set state at (rho2) and find equilibrium P2, T2
        # such that the Hugoniot energy equation is satisfied.

        # Iterate on P2:
        P2_lo, P2_hi = 2 * P0, 100 * P0
        converged = False
        for _ in range(100):
            P2 = 0.5 * (P2_lo + P2_hi)
            h2_hugoniot = h1 + 0.5 * (P2 + P0) * (v1 - v2)

            try:
                gas2.HPX = h2_hugoniot, P2, COMP
                gas2.equilibrate("HP", max_steps=5000)
            except ct.CanteraError:
                P2_lo = P2
                continue

            rho2_eq = gas2.density
            # We want rho2_eq = rho2
            if rho2_eq > rho2:
                P2_hi = P2  # P2 too high -> too dense
            else:
                P2_lo = P2  # P2 too low -> too sparse

            if abs(rho2_eq - rho2) / rho2 < 1e-8:
                converged = True
                break

        if not converged:
            continue

        # Now compute D from Rayleigh line: D^2 = (P2 - P1) / (rho1^2 * (v1 - v2))
        dP = P2 - P0
        dv = v1 - v2
        if dP <= 0 or dv <= 0:
            continue

        D2 = dP / (rho1**2 * dv)
        if D2 > 0:
            D = np.sqrt(D2)
            D_vals.append(D)
            valid_etas.append(eta)

    D_vals = np.array(D_vals)
    valid_etas = np.array(valid_etas)

    # CJ = minimum D
    idx_cj = np.argmin(D_vals)
    D_cj = D_vals[idx_cj]
    eta_cj = valid_etas[idx_cj]

    # Recompute CJ state at the minimum
    v2_cj = v1 / eta_cj
    P2_lo, P2_hi = 2 * P0, 100 * P0
    for _ in range(100):
        P2 = 0.5 * (P2_lo + P2_hi)
        h2 = h1 + 0.5 * (P2 + P0) * (v1 - v2_cj)
        gas2.HPX = h2, P2, COMP
        gas2.equilibrate("HP", max_steps=5000)
        rho2_eq = gas2.density
        rho2_target = rho1 * eta_cj
        if rho2_eq > rho2_target:
            P2_hi = P2
        else:
            P2_lo = P2
        if abs(rho2_eq - rho2_target) / rho2_target < 1e-10:
            break

    gamma2 = gas2.cp / gas2.cv
    a2 = np.sqrt(gamma2 * ct.gas_constant * gas2.T / gas2.mean_molecular_weight)

    return {
        "D_CJ": D_cj,
        "T_CJ": gas2.T,
        "P_CJ": gas2.P,
        "rho_CJ": gas2.density,
        "gamma_CJ": gamma2,
        "a_CJ": a2,
        "eta_CJ": eta_cj,
        "rho1": rho1,
    }


def main():
    print("=" * 60)
    print("Phase 2: Independent CJ Reference — Paper [2]")
    print("Sun et al., CPC 292 (2023) 108859")
    print("=" * 60)

    gas = ct.Solution("h2o2.yaml")
    gas.TPX = T0, P0, COMP
    print(f"\nMechanism: h2o2.yaml ({gas.n_species} sp, {gas.n_reactions} rxn)")
    print(f"Mixture: {COMP}")
    print(f"T0={T0} K, P0={P0/ct.one_atm:.1f} atm, rho0={gas.density:.4f} kg/m3")

    print("\nComputing CJ properties (Hugoniot sweep)...")
    cj = compute_cj()

    print(f"\n  V_CJ  = {cj['D_CJ']:.1f} m/s")
    print(f"  T_CJ  = {cj['T_CJ']:.1f} K")
    print(f"  P_CJ  = {cj['P_CJ']/ct.one_atm:.2f} atm")
    print(f"  rho_CJ = {cj['rho_CJ']:.4f} kg/m3")
    print(f"  gamma  = {cj['gamma_CJ']:.4f}")
    print(f"  a_CJ   = {cj['a_CJ']:.1f} m/s")
    print(f"  eta_CJ = {cj['eta_CJ']:.4f}")

    # Compare with literature
    ref = {"V_CJ": 1968.0, "P_CJ_atm": 15.6, "T_CJ_K": 2950.0}
    v_err = abs(cj["D_CJ"] - ref["V_CJ"]) / ref["V_CJ"] * 100
    p_err = abs(cj["P_CJ"] / ct.one_atm - ref["P_CJ_atm"]) / ref["P_CJ_atm"] * 100
    t_err = abs(cj["T_CJ"] - ref["T_CJ_K"]) / ref["T_CJ_K"] * 100

    print(f"\n--- Literature comparison ---")
    print(f"  V_CJ: {cj['D_CJ']:.1f} vs {ref['V_CJ']:.0f} m/s  (err={v_err:.1f}%)")
    print(f"  P_CJ: {cj['P_CJ']/ct.one_atm:.2f} vs {ref['P_CJ_atm']:.1f} atm  (err={p_err:.1f}%)")
    print(f"  T_CJ: {cj['T_CJ']:.0f} vs {ref['T_CJ_K']:.0f} K  (err={t_err:.1f}%)")

    verdict = "PASS" if v_err < 2 and p_err < 5 and t_err < 5 else "INVESTIGATE"
    print(f"\n  Verdict: {verdict}")

    # Save
    results = {
        "mixture": COMP,
        "T0_K": T0,
        "P0_Pa": P0,
        "rho0_kgm3": round(cj["rho1"], 6),
        "V_CJ_ms": round(cj["D_CJ"], 2),
        "T_CJ_K": round(cj["T_CJ"], 2),
        "P_CJ_Pa": round(cj["P_CJ"], 2),
        "P_CJ_atm": round(cj["P_CJ"] / ct.one_atm, 3),
        "rho_CJ_kgm3": round(cj["rho_CJ"], 6),
        "gamma_CJ": round(cj["gamma_CJ"], 4),
        "a_CJ_ms": round(cj["a_CJ"], 2),
        "eta_CJ": round(cj["eta_CJ"], 4),
        "errors_pct": {"V_CJ": round(v_err, 2), "P_CJ": round(p_err, 2), "T_CJ": round(t_err, 2)},
        "verdict": verdict,
        "cantera_version": ct.__version__,
        "mechanism": "h2o2.yaml (Cantera built-in)",
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "cj_reference.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
