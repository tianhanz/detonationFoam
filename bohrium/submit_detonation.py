#!/usr/bin/env python3
"""Submit detonationFoam jobs to Bohrium cloud compute.

Packages an OpenFOAM case directory into a Bohrium container job for
parallel MPI execution. Designed for detonationFoam V2.0 on OpenFOAM 9.

Usage:
    # Submit a case with default settings (8 cores)
    python submit_detonation.py cases/1D_H2O2_detonation

    # Submit with more cores and longer runtime
    python submit_detonation.py cases/1D_H2O2_detonation --np 32 --machine c32_m64_cpu --max-time 720

    # Dry run
    python submit_detonation.py cases/1D_H2O2_detonation --dry-run

    # Poll until completion
    python submit_detonation.py cases/1D_H2O2_detonation --poll

Prerequisites:
    - bohr CLI installed (~/.bohrium/bohr)
    - ACCESS_KEY and PROJECT_ID set in environment or ~/.openclaw/openclaw.json
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Defaults
PROJ_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IMAGE = "microfluidica/openfoam:9"  # public Docker Hub image
DEFAULT_MACHINE = "c8_m32_cpu"  # 8 cores, 32 GB — good for 1D detonation
DEFAULT_MAX_RUN_TIME = 360  # 6 hours
DEFAULT_DISK_SIZE = 30  # GB
DEFAULT_NP = 8  # MPI processes

BOHR_BIN = os.path.expanduser("~/.bohrium/bohr")
BOHR_ENV: dict[str, str] = {}


def _load_bohrium_env():
    """Load ACCESS_KEY and PROJECT_ID from environment or openclaw config."""
    global BOHR_ENV
    env = os.environ.copy()
    env["OPENAPI_HOST"] = "https://openapi.dp.tech"
    env["TIEFBLUE_HOST"] = "https://tiefblue.dp.tech"

    oc_path = Path.home() / ".openclaw" / "openclaw.json"
    if oc_path.exists():
        try:
            with open(oc_path) as f:
                oc = json.load(f)
            bj = oc.get("bohrium-job", {}).get("env", {})
            if bj.get("ACCESS_KEY"):
                env.setdefault("ACCESS_KEY", bj["ACCESS_KEY"])
            if bj.get("PROJECT_ID"):
                env.setdefault("PROJECT_ID", str(bj["PROJECT_ID"]))
        except (json.JSONDecodeError, KeyError):
            pass

    for key in ("ACCESS_KEY", "PROJECT_ID"):
        if os.environ.get(key):
            env[key] = os.environ[key]

    BOHR_ENV = env
    return env


def _bohr_run(args_str: str) -> subprocess.CompletedProcess:
    """Run a bohr CLI command via pseudo-TTY wrapper."""
    cmd = f"{BOHR_BIN} {args_str}"
    return subprocess.run(
        ["script", "-qc", cmd, "/dev/null"],
        capture_output=True, text=True, env=BOHR_ENV, timeout=120,
    )


def prepare_case(case_dir: Path, np: int, tmp_base: Path) -> Path:
    """Prepare a self-contained input directory for Bohrium.

    Copies the case directory and creates a run.sh wrapper that:
    1. Sources OpenFOAM 9 environment
    2. Compiles detonationFoam if not pre-built (for base OF9 image)
    3. Runs blockMesh, setFields, decomposePar
    4. Runs mpirun -np N detonationFoam_V2.0 -parallel
    5. Reconstructs results
    """
    input_dir = tmp_base / case_dir.name
    shutil.copytree(case_dir, input_dir)

    # Copy solver source for compilation on Bohrium
    solver_src = PROJ_ROOT / "applications"
    if solver_src.is_dir():
        shutil.copytree(
            solver_src, input_dir / "applications",
            ignore=shutil.ignore_patterns(
                "*.o", "*.dep", "lnInclude", "linux64*", "__pycache__"
            ),
        )

    # Update decomposeParDict for the requested number of processors
    decompose_file = input_dir / "system" / "decomposeParDict"
    if decompose_file.exists():
        text = decompose_file.read_text()
        # Replace numberOfSubdomains
        import re
        text = re.sub(
            r'numberOfSubdomains\s+\d+',
            f'numberOfSubdomains  {np}',
            text
        )
        # Replace simple decomposition coefficients for 1D
        text = re.sub(
            r'n\s+\(\s*\d+\s+\d+\s+\d+\s*\)',
            f'n               ({np} 1 1)',
            text
        )
        decompose_file.write_text(text)

    # Create run.sh
    run_sh = input_dir / "run.sh"
    run_sh.write_text(f"""\
#!/bin/bash
set -e

echo "=== detonationFoam Bohrium Job ==="
echo "Date: $(date)"
echo "Host: $(hostname)"
echo "Cores: $(nproc)"
echo "MPI procs: {np}"

# Source OpenFOAM 9
source /opt/openfoam9/etc/bashrc

# Compile detonationFoam from source
echo "=== Compiling detonationFoam ==="
cd applications/solvers/detonationFoam_V2.0

# Compile libraries
cd fluxSchemes_improved && wmake libso 2>&1 | tail -3 && cd ..
cd ../../../applications/libraries/DLBFoam-1.0-1.0_OF8/src && wmake libso 2>&1 | tail -3 && cd ../../../..
cd applications/libraries/dynamicMesh2D && wmake libso 2>&1 | tail -3 && cd ../../..
cd applications/libraries/dynamicFvMesh2D && wmake libso 2>&1 | tail -3 && cd ../../..

# Compile solver
cd applications/solvers/detonationFoam_V2.0 && wmake 2>&1 | tail -5 && cd ../../..

echo "=== Solver compiled ==="
which detonationFoam_V2.0

# Run case
echo "=== Setting up case ==="
blockMesh 2>&1 | tail -5
setFields 2>&1 | tail -5

echo "=== Decomposing for {np} processors ==="
decomposePar 2>&1 | tail -5

echo "=== Running detonationFoam ==="
mpirun -np {np} --allow-run-as-root --oversubscribe detonationFoam_V2.0 -parallel 2>&1 | tee run.log

echo "=== Reconstructing ==="
reconstructPar 2>&1 | tail -10

echo "=== Job complete ==="
echo "Date: $(date)"
ls -la
""", encoding="utf-8")

    return input_dir


def submit_job(case_name: str, input_dir: Path, project_id: int,
               machine: str, image: str, max_time: int, disk: int) -> str | None:
    """Submit a job to Bohrium."""
    job_config = {
        "job_name": f"detonationFoam-{case_name}",
        "command": "bash run.sh",
        "log_file": "run.log",
        "backward_files": [],  # keep everything
        "project_id": project_id,
        "machine_type": machine,
        "image_address": image,
        "job_type": "container",
        "disk_size": disk,
        "max_run_time": max_time,
        "max_reschedule_times": 1,
    }

    job_json = input_dir / "job.json"
    job_json.write_text(json.dumps(job_config, indent=2))

    result = _bohr_run(f"job submit -i {job_json} -p {input_dir}")
    if result.returncode == 0:
        output = result.stdout.strip()
        for line in output.splitlines():
            if "jobid" in line.lower() or "JobId" in line:
                return line.split(":")[-1].strip()
        return output
    else:
        print(f"SUBMIT FAILED: {result.stderr.strip()}")
        print(f"stdout: {result.stdout.strip()}")
        return None


def poll_jobs(job_ids: list[str], interval: int = 60):
    """Poll Bohrium REST API for job status."""
    import urllib.request

    ak = BOHR_ENV.get("ACCESS_KEY", "")
    base = "https://openapi.dp.tech/openapi/v1"
    status_map = {0: "Pending", 1: "Running", 2: "Finished", 3: "Scheduling", -1: "Failed"}
    track_ids = set(str(j) for j in job_ids)

    print(f"\nPolling {len(job_ids)} jobs every {interval}s...")
    while True:
        try:
            req = urllib.request.Request(
                f"{base}/job/list?page=1&pageSize={len(job_ids) + 10}",
                headers={"accessKey": ak},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read())
        except Exception as e:
            print(f"[WARN] API error: {e}")
            time.sleep(interval)
            continue

        items = body.get("data", {}).get("items", [])
        active = 0
        for item in items:
            jid = str(item.get("jobId") or "")
            name = item.get("jobName", "")
            if jid in track_ids:
                st = item.get("status", "?")
                label = status_map.get(st, str(st))
                if st in (0, 1, 3):
                    active += 1
                print(f"  [{label}] {name} (id={jid})")

        if active == 0:
            print("\nAll jobs finished.")
            break

        print(f"  {active} active, checking again in {interval}s...")
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped polling.")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Submit detonationFoam jobs to Bohrium cloud compute"
    )
    parser.add_argument("case", type=Path, help="Path to OpenFOAM case directory")
    parser.add_argument("--np", type=int, default=DEFAULT_NP,
                        help=f"MPI processes (default: {DEFAULT_NP})")
    parser.add_argument("--project-id", type=int, default=0,
                        help="Bohrium project ID")
    parser.add_argument("--machine", default=DEFAULT_MACHINE,
                        help=f"Machine type (default: {DEFAULT_MACHINE})")
    parser.add_argument("--image", default=DEFAULT_IMAGE,
                        help=f"Docker image (default: {DEFAULT_IMAGE})")
    parser.add_argument("--max-time", type=int, default=DEFAULT_MAX_RUN_TIME,
                        help=f"Max run time in minutes (default: {DEFAULT_MAX_RUN_TIME})")
    parser.add_argument("--disk", type=int, default=DEFAULT_DISK_SIZE,
                        help=f"Disk size in GB (default: {DEFAULT_DISK_SIZE})")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll", action="store_true")
    parser.add_argument("--download", type=Path, default=None)
    args = parser.parse_args()

    if args.project_id == 0:
        args.project_id = int(BOHR_ENV.get("PROJECT_ID", "0"))
    if args.project_id == 0:
        print("Error: set PROJECT_ID env var or use --project-id")
        sys.exit(1)

    case_dir = args.case.resolve()
    if not case_dir.is_dir():
        print(f"Error: case directory not found: {case_dir}")
        sys.exit(1)

    case_name = case_dir.name
    print(f"Case       : {case_name}")
    print(f"MPI procs  : {args.np}")
    print(f"Machine    : {args.machine}")
    print(f"Image      : {args.image}")
    print(f"Max time   : {args.max_time} min")
    print(f"Project ID : {args.project_id}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would submit {case_name}. No job created.")
        return

    tmp_base = Path(tempfile.mkdtemp(prefix=f"bohrium_{case_name}_"))
    print(f"Staging to : {tmp_base}")

    input_dir = prepare_case(case_dir, args.np, tmp_base)
    job_id = submit_job(case_name, input_dir, args.project_id,
                        args.machine, args.image, args.max_time, args.disk)

    if job_id:
        print(f"\nSubmitted: Job ID = {job_id}")
        if args.poll:
            poll_jobs([job_id])
        if args.download:
            args.download.mkdir(parents=True, exist_ok=True)
            print(f"Downloading to {args.download}...")
            _bohr_run(f"job download -j {job_id} -o {args.download}")
    else:
        print("\nSubmission failed.")
        sys.exit(1)


if __name__ == "__main__":
    _load_bohrium_env()
    main()
