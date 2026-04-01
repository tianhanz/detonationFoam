#!/usr/bin/env python3
"""Post-process grid convergence study results.

Reads reconstructed OpenFOAM time directories from each convergence case
and computes:
  1. CJ detonation velocity (shock position tracking)
  2. Peak pressure behind shock
  3. ZND induction length (shock to 50% peak temperature rise)
  4. Pressure and temperature profiles at a fixed time

Generates convergence plots and a summary table.

Usage:
    python analyze_convergence.py                    # analyze all cases
    python analyze_convergence.py --time 5e-6        # profiles at t=5μs
    python analyze_convergence.py --plot              # generate plots
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

CASE_DIR = Path(__file__).resolve().parent.parent / "case"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FIG_DIR = Path(__file__).resolve().parent.parent / "figures"

CASES = ["uniform_dx40", "uniform_dx20", "uniform_dx10", "uniform_dx05", "amr_base40_L2"]
DX_MAP = {
    "uniform_dx40": 40e-6,
    "uniform_dx20": 20e-6,
    "uniform_dx10": 10e-6,
    "uniform_dx05": 5e-6,
    "amr_base40_L2": 10e-6,  # effective resolution
}

# Reference CJ values
CJ_REF_FILE = DATA_DIR / "cj_reference.json"


def get_time_dirs(case_path):
    """Get sorted list of time directories (float values)."""
    times = []
    for d in case_path.iterdir():
        if d.is_dir():
            try:
                t = float(d.name)
                if t > 0:
                    times.append((t, d))
            except ValueError:
                continue
    return sorted(times, key=lambda x: x[0])


def read_scalar_field(field_path):
    """Read an OpenFOAM volScalarField and return values as numpy array."""
    with open(field_path) as f:
        lines = f.readlines()

    # Find the internalField section
    in_field = False
    n_values = 0
    values = []
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("internalField"):
            if "uniform" in line and "nonuniform" not in line:
                # Uniform field — extract value
                val = float(line.split("uniform")[1].strip().rstrip(";"))
                return np.array([val])
            # Non-uniform list
            in_field = True
            continue
        if in_field and not n_values:
            try:
                n_values = int(line)
                continue
            except ValueError:
                continue
        if in_field and line == "(":
            continue
        if in_field and line == ")":
            break
        if in_field and n_values:
            try:
                values.append(float(line))
            except ValueError:
                continue

    return np.array(values)


def get_cell_centers_x(case_path, time_dir):
    """Get cell center x-coordinates.

    For AMR cases: reads the Cx field (written by writeCellCentres postProcess).
    For uniform cases: computes from blockMeshDict.
    """
    # Try Cx field first (works for AMR with varying cell count)
    cx_file = time_dir / "Cx"
    if cx_file.exists():
        return read_scalar_field(cx_file)

    # Uniform case: compute from blockMeshDict
    bmdict = case_path / "system" / "blockMeshDict"
    with open(bmdict) as f:
        content = f.read()

    hex_match = re.search(r"hex\s+\([^)]+\)\s+\((\d+)\s+\d+\s+\d+\)", content)
    if not hex_match:
        return None

    ncells = int(hex_match.group(1))

    vert_section = re.search(r"vertices\s*\((.*?)\)\s*;\s*\n", content, re.DOTALL)
    if not vert_section:
        dx = 0.05 / ncells
        return np.linspace(dx / 2, 0.05 - dx / 2, ncells)

    verts_text = vert_section.group(1)
    x_vals = []
    for m in re.finditer(r"\(\s*([0-9.e+-]+)\s+[0-9.e+-]+\s+[0-9.e+-]+\s*\)", verts_text):
        x_vals.append(float(m.group(1)))

    if x_vals:
        x_min = min(x_vals)
        x_max = max(x_vals)
        dx = (x_max - x_min) / ncells
        return np.linspace(x_min + dx / 2, x_max - dx / 2, ncells)

    dx = 0.05 / ncells
    return np.linspace(dx / 2, 0.05 - dx / 2, ncells)


def find_shock_position(x, p, threshold_factor=3.0):
    """Find shock position as the location of maximum pressure gradient."""
    if len(p) < 3:
        return None, None

    # Shock is where pressure jumps most sharply
    dp = np.diff(p)
    idx = np.argmax(np.abs(dp))

    # Also find peak pressure
    p_max = np.max(p)

    return x[idx], p_max


def compute_induction_length(x, T, shock_x):
    """Compute ZND induction length: distance from shock to 50% peak T rise."""
    if shock_x is None:
        return None

    # Find post-shock region (behind the shock, x < shock_x for right-traveling)
    mask = x < shock_x
    if not np.any(mask):
        return None

    x_post = x[mask]
    T_post = T[mask]

    T_min = T_post[-1] if len(T_post) > 0 else 300  # near shock
    T_max = np.max(T_post)
    T_half = T_min + 0.5 * (T_max - T_min)

    # Find where T first exceeds T_half (searching from shock backward)
    for i in range(len(T_post) - 1, -1, -1):
        if T_post[i] > T_half:
            return shock_x - x_post[i]

    return None


def analyze_case(case_name, profile_time=None):
    """Analyze a single convergence case."""
    case_path = CASE_DIR / case_name

    if not case_path.exists():
        return None

    time_dirs = get_time_dirs(case_path)
    if not time_dirs:
        print(f"  {case_name}: No time directories found (not yet run?)")
        return None

    print(f"  {case_name}: {len(time_dirs)} time steps, t=[{time_dirs[0][0]:.2e}, {time_dirs[-1][0]:.2e}]")

    # Track shock position at each time
    shock_data = []
    profile_data = None

    for t, tdir in time_dirs:
        p_file = tdir / "p"
        T_file = tdir / "T"

        if not p_file.exists():
            continue

        p = read_scalar_field(p_file)
        if len(p) <= 1:
            continue

        x = get_cell_centers_x(case_path, tdir)
        if x is None or len(x) != len(p):
            # For AMR, cell count changes — skip if mismatch
            continue

        # Sort by x (AMR cells may be in arbitrary order)
        sort_idx = np.argsort(x)
        x = x[sort_idx]
        p = p[sort_idx]

        shock_x, p_max = find_shock_position(x, p)
        shock_data.append({"t": t, "shock_x": shock_x, "p_max": p_max})

        # Extract profile at requested time
        if profile_time is not None and T_file.exists():
            if abs(t - profile_time) < 0.3e-6:  # within 0.3 μs
                T = read_scalar_field(T_file)
                if len(T) == len(sort_idx):
                    T = T[sort_idx]  # apply same sort as x/p
                    induction = compute_induction_length(x, T, shock_x)
                    profile_data = {
                        "t": t,
                        "x": x.tolist(),
                        "p": p.tolist(),
                        "T": T.tolist(),
                        "shock_x": shock_x,
                        "p_max": p_max,
                        "induction_length": induction,
                    }

    if len(shock_data) < 2:
        return {"case": case_name, "error": "insufficient time steps"}

    # Compute CJ velocity from shock trajectory
    # Use points after 0.5 μs (driver influence dissipated)
    late_data = [d for d in shock_data if d["t"] > 0.5e-6 and d["shock_x"] is not None]

    if len(late_data) >= 2:
        ts = np.array([d["t"] for d in late_data])
        xs = np.array([d["shock_x"] for d in late_data])

        # Linear fit: x = V*t + b
        coeffs = np.polyfit(ts, xs, 1)
        V_cj = coeffs[0]

        # Also compute instantaneous velocities
        if len(ts) > 1:
            V_inst = np.diff(xs) / np.diff(ts)
        else:
            V_inst = np.array([V_cj])
    else:
        V_cj = None
        V_inst = np.array([])

    # Average peak pressure (last 3 time steps)
    p_maxes = [d["p_max"] for d in shock_data[-3:] if d["p_max"] is not None]
    p_max_avg = np.mean(p_maxes) if p_maxes else None

    result = {
        "case": case_name,
        "dx": DX_MAP[case_name],
        "n_timesteps": len(time_dirs),
        "t_range": [time_dirs[0][0], time_dirs[-1][0]],
        "V_cj": V_cj,
        "V_inst_mean": float(np.mean(V_inst)) if len(V_inst) > 0 else None,
        "V_inst_std": float(np.std(V_inst)) if len(V_inst) > 0 else None,
        "p_max_avg": p_max_avg,
        "shock_trajectory": [
            {"t": d["t"], "x": d["shock_x"], "p_max": d["p_max"]}
            for d in shock_data
        ],
    }

    if profile_data:
        result["profile"] = profile_data

    return result


def print_summary(results, cj_ref):
    """Print convergence summary table."""
    print("\n" + "=" * 80)
    print("GRID CONVERGENCE SUMMARY")
    print("=" * 80)

    V_ref = cj_ref.get("V_CJ_ms", 1976.3) if cj_ref else 1976.3
    P_ref = cj_ref.get("P_CJ_Pa", 1577966) if cj_ref else 1577966

    fmt = "{:<18s} {:>8s} {:>10s} {:>8s} {:>10s} {:>8s} {:>12s}"
    print(fmt.format("Case", "dx(um)", "V_CJ(m/s)", "err(%)", "P_max(atm)", "err(%)", "Induction(mm)"))
    print("-" * 80)

    for r in results:
        if r is None:
            continue
        if "error" in r:
            print(f"  {r['case']}: {r.get('error', 'no data')}")
            continue

        dx_um = f"{r['dx']*1e6:.0f}"
        v_str = f"{r['V_cj']:.1f}" if r["V_cj"] else "—"
        v_err = f"{abs(r['V_cj'] - V_ref)/V_ref*100:.2f}" if r["V_cj"] else "—"
        p_str = f"{r['p_max_avg']/101325:.2f}" if r["p_max_avg"] else "—"
        p_err = f"{abs(r['p_max_avg'] - P_ref)/P_ref*100:.1f}" if r["p_max_avg"] else "—"

        ind_str = "—"
        if r.get("profile") and r["profile"].get("induction_length"):
            ind_str = f"{r['profile']['induction_length']*1000:.3f}"

        print(fmt.format(r["case"], dx_um, v_str, v_err, p_str, p_err, ind_str))

    # Richardson extrapolation for uniform cases
    uniform_results = [r for r in results if r and "error" not in r and "uniform" in r["case"] and r["V_cj"]]
    if len(uniform_results) >= 3:
        print("\n--- Richardson Extrapolation (finest 3 uniform grids) ---")
        # Sort by dx (finest last)
        uniform_results.sort(key=lambda r: r["dx"], reverse=True)
        r = 2.0  # refinement ratio
        V3 = uniform_results[-1]["V_cj"]  # finest
        V2 = uniform_results[-2]["V_cj"]
        V1 = uniform_results[-3]["V_cj"]

        if abs(V2 - V3) > 1e-10:
            p_est = np.log(abs((V1 - V2) / (V2 - V3))) / np.log(r)
            V_ext = V3 + (V3 - V2) / (r ** p_est - 1) if p_est > 0 else V3
            print(f"  Estimated order of convergence: p = {p_est:.2f}")
            print(f"  Richardson-extrapolated V_CJ: {V_ext:.1f} m/s")
            print(f"  Error vs Cantera CJ ({V_ref:.1f}): {abs(V_ext - V_ref)/V_ref*100:.3f}%")
        else:
            print("  V2 ≈ V3 — already converged")

    # AMR vs uniform comparison
    amr_result = next((r for r in results if r and "error" not in r and "amr" in r["case"]), None)
    uni10_result = next((r for r in results if r and "error" not in r and r["case"] == "uniform_dx10"), None)
    if amr_result and uni10_result and amr_result["V_cj"] and uni10_result["V_cj"]:
        print("\n--- AMR vs Uniform (same effective dx=10μm) ---")
        print(f"  AMR  V_CJ = {amr_result['V_cj']:.1f} m/s")
        print(f"  Uni  V_CJ = {uni10_result['V_cj']:.1f} m/s")
        diff = abs(amr_result["V_cj"] - uni10_result["V_cj"])
        print(f"  Difference: {diff:.1f} m/s ({diff/uni10_result['V_cj']*100:.3f}%)")


def make_plots(results, cj_ref):
    """Generate convergence plots (requires matplotlib)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available — skipping plots")
        return

    FIG_DIR.mkdir(exist_ok=True)
    V_ref = cj_ref.get("V_CJ_ms", 1976.3) if cj_ref else 1976.3

    # Plot 1: V_CJ vs dx
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    for r in results:
        if r is None or "error" in r or r["V_cj"] is None:
            continue
        marker = "s" if "amr" in r["case"] else "o"
        color = "red" if "amr" in r["case"] else "blue"
        label = "AMR" if "amr" in r["case"] else "Uniform"
        ax.plot(r["dx"] * 1e6, r["V_cj"], marker, color=color, markersize=8, label=label)

    ax.axhline(y=V_ref, color="k", linestyle="--", alpha=0.5, label=f"CJ ref ({V_ref:.1f})")
    ax.set_xlabel("dx (μm)")
    ax.set_ylabel("V_CJ (m/s)")
    ax.set_title("Grid Convergence: CJ Detonation Velocity")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "convergence_velocity.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {FIG_DIR / 'convergence_velocity.png'}")

    # Plot 2: Shock trajectories
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    for r in results:
        if r is None or "error" in r:
            continue
        traj = r.get("shock_trajectory", [])
        if not traj:
            continue
        ts = [d["t"] * 1e6 for d in traj if d["x"] is not None]
        xs = [d["x"] * 1000 for d in traj if d["x"] is not None]
        style = "--" if "amr" in r["case"] else "-"
        ax.plot(ts, xs, style, label=r["case"])

    ax.set_xlabel("Time (μs)")
    ax.set_ylabel("Shock position (mm)")
    ax.set_title("Shock Trajectories")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "convergence_trajectories.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {FIG_DIR / 'convergence_trajectories.png'}")

    # Plot 3: Pressure profiles at fixed time (if available)
    has_profiles = any(r and r.get("profile") for r in results)
    if has_profiles:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        for r in results:
            if r is None or not r.get("profile"):
                continue
            prof = r["profile"]
            x_mm = np.array(prof["x"]) * 1000
            p_atm = np.array(prof["p"]) / 101325
            T_K = np.array(prof["T"])
            style = "--" if "amr" in r["case"] else "-"
            ax1.plot(x_mm, p_atm, style, label=r["case"], linewidth=0.8)
            ax2.plot(x_mm, T_K, style, label=r["case"], linewidth=0.8)

        ax1.set_ylabel("Pressure (atm)")
        ax1.set_title("Detonation Wave Profiles")
        ax1.legend(fontsize=7)
        ax1.grid(True, alpha=0.3)

        ax2.set_xlabel("x (mm)")
        ax2.set_ylabel("Temperature (K)")
        ax2.legend(fontsize=7)
        ax2.grid(True, alpha=0.3)

        fig.tight_layout()
        fig.savefig(FIG_DIR / "convergence_profiles.png", dpi=150)
        plt.close(fig)
        print(f"  Saved: {FIG_DIR / 'convergence_profiles.png'}")


def main():
    parser = argparse.ArgumentParser(description="Analyze grid convergence results")
    parser.add_argument("--time", type=float, default=5e-6,
                        help="Time for profile extraction (default: 5e-6)")
    parser.add_argument("--plot", action="store_true", help="Generate plots")
    args = parser.parse_args()

    print("=" * 60)
    print("Grid Convergence Analysis — Paper [2]")
    print("=" * 60)

    # Load CJ reference
    cj_ref = None
    if CJ_REF_FILE.exists():
        with open(CJ_REF_FILE) as f:
            cj_ref = json.load(f)
        print(f"CJ reference: V={cj_ref['V_CJ_ms']} m/s, P={cj_ref['P_CJ_atm']} atm")

    print(f"\nProfile extraction time: {args.time*1e6:.1f} μs\n")

    # Analyze each case
    results = []
    for case_name in CASES:
        r = analyze_case(case_name, profile_time=args.time)
        results.append(r)

    # Summary table
    print_summary(results, cj_ref)

    # Save results
    DATA_DIR.mkdir(exist_ok=True)
    save_results = []
    for r in results:
        if r is None:
            continue
        # Remove large arrays for JSON serialization
        r_save = {k: v for k, v in r.items() if k != "profile"}
        if r.get("profile"):
            r_save["profile_time"] = r["profile"]["t"]
            r_save["induction_length"] = r["profile"].get("induction_length")
        save_results.append(r_save)

    out_file = DATA_DIR / "convergence_results.json"
    with open(out_file, "w") as f:
        json.dump(save_results, f, indent=2, default=str)
    print(f"\nSaved results to {out_file}")

    # Plots
    if args.plot:
        print("\nGenerating plots...")
        make_plots(results, cj_ref)

    print("\nDone.")


if __name__ == "__main__":
    main()
