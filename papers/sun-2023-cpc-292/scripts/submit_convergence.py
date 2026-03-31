#!/usr/bin/env python3
"""Submit all grid convergence cases to Bohrium.

Usage:
    python submit_convergence.py           # submit all 5 cases
    python submit_convergence.py --dry-run # show what would be submitted
    python submit_convergence.py --case uniform_dx10  # submit one case
"""

import argparse
import sys
from pathlib import Path

# Add bohrium tools to path
PROJ_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJ_ROOT / "bohrium"))

from submit_detonation import (
    _load_bohrium_env,
    prepare_case,
    submit_job,
    poll_jobs,
    BOHR_ENV,
    DEFAULT_IMAGE,
    DEFAULT_DISK_SIZE,
)

CASE_DIR = Path(__file__).resolve().parent.parent / "case"

# All convergence cases with their Bohrium settings
# Coarser cases are cheap → c4_m8_cpu; finest needs more time
CASES = {
    "uniform_dx40": {"np": 4, "machine": "c4_m8_cpu", "max_time": 60},
    "uniform_dx20": {"np": 4, "machine": "c4_m8_cpu", "max_time": 120},
    "uniform_dx10": {"np": 4, "machine": "c4_m8_cpu", "max_time": 240},
    "uniform_dx05": {"np": 4, "machine": "c4_m8_cpu", "max_time": 360},
    "amr_base40_L2": {"np": 4, "machine": "c4_m8_cpu", "max_time": 240},
}


def main():
    parser = argparse.ArgumentParser(description="Submit grid convergence jobs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--case", type=str, help="Submit only this case")
    parser.add_argument("--poll", action="store_true", help="Poll until all jobs finish")
    args = parser.parse_args()

    env = _load_bohrium_env()
    project_id = int(env.get("PROJECT_ID", "0"))
    if project_id == 0:
        print("Error: set PROJECT_ID env var")
        sys.exit(1)

    cases_to_run = {args.case: CASES[args.case]} if args.case else CASES

    print("=" * 60)
    print("Grid Convergence — Bohrium Batch Submission")
    print("=" * 60)

    import tempfile
    tmp_base = Path(tempfile.mkdtemp(prefix="bohrium_convergence_"))

    job_ids = []
    for name, cfg in cases_to_run.items():
        case_path = CASE_DIR / name
        if not case_path.exists():
            print(f"  SKIP: {name} — case directory not found")
            continue

        is_amr = (case_path / "constant" / "dynamicMeshDict").exists()
        print(f"\n  {name}: np={cfg['np']}, machine={cfg['machine']}, max_time={cfg['max_time']}min, AMR={is_amr}")

        if args.dry_run:
            print(f"    [DRY RUN] Would submit {name}")
            continue

        input_dir = prepare_case(case_path, cfg["np"], tmp_base, is_amr)
        job_id = submit_job(
            f"convergence-{name}",
            input_dir,
            project_id,
            cfg["machine"],
            DEFAULT_IMAGE,
            cfg["max_time"],
            DEFAULT_DISK_SIZE,
        )

        if job_id:
            print(f"    Submitted: Job ID = {job_id}")
            job_ids.append(job_id)
        else:
            print(f"    FAILED to submit {name}")

    if job_ids:
        print(f"\n  Submitted {len(job_ids)} jobs: {job_ids}")
        if args.poll:
            poll_jobs(job_ids)

    print("\nDone.")


if __name__ == "__main__":
    main()
