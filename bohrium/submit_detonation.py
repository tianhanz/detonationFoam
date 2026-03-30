#!/usr/bin/env python3
"""Submit detonationFoam jobs to Bohrium cloud compute.

Uses a pre-compiled Docker image with OF9 + detonationFoam. No compilation
needed on Bohrium — just blockMesh, setFields, decomposePar, and run.

Usage:
    python submit_detonation.py cases/1D_H2O2_detonation --np 4
    python submit_detonation.py cases/2D_AMR_test --np 4
    python submit_detonation.py cases/1D_H2O2_detonation --np 4 --poll
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IMAGE = "registry.dp.tech/dptech/dp/native/prod-1408/detonationfoam:0.2"
DEFAULT_MACHINE = "c4_m8_cpu"
DEFAULT_MAX_RUN_TIME = 360
DEFAULT_DISK_SIZE = 30
DEFAULT_NP = 4

BOHR_BIN = os.path.expanduser("~/.bohrium/bohr")
BOHR_ENV: dict[str, str] = {}


def _load_bohrium_env():
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
    cmd = f"{BOHR_BIN} {args_str}"
    return subprocess.run(
        ["script", "-qc", cmd, "/dev/null"],
        capture_output=True, text=True, env=BOHR_ENV, timeout=600,
    )


def prepare_case(case_dir: Path, np: int, tmp_base: Path, is_amr: bool) -> Path:
    """Prepare input directory for Bohrium. No solver source needed — image is pre-compiled."""
    input_dir = tmp_base / case_dir.name

    # Copy case files only (no solver source)
    shutil.copytree(
        case_dir, input_dir,
        ignore=shutil.ignore_patterns(
            "processor*", "log.*", "constant/polyMesh", "*.foam~"
        ),
    )

    # Update numberOfSubdomains
    decompose_file = input_dir / "system" / "decomposeParDict"
    if decompose_file.exists():
        text = decompose_file.read_text()
        text = re.sub(r'numberOfSubdomains\s+\d+', f'numberOfSubdomains  {np}', text)
        decompose_file.write_text(text)

    # AMR cases need dynamicMeshDict copied to processor dirs after decomposePar
    amr_extra = ""
    if is_amr:
        amr_extra = """
echo "=== Copying dynamicMeshDict to processor directories ==="
for d in processor*/; do
    cp constant/dynamicMeshDict "$d/constant/" 2>/dev/null || true
done
"""

    run_sh = input_dir / "run.sh"
    run_sh.write_text(f"""\
#!/bin/bash
# Redirect ALL output to run.log so Bohrium can capture it
exec > >(tee run.log) 2>&1
set -e

echo "=== detonationFoam Bohrium Job ==="
echo "Date: $(date)"
echo "Host: $(hostname)"
echo "Cores: $(nproc)"
echo "MPI procs: {np}"
echo "Working dir: $(pwd)"
ls -la

# Source OF9 (pre-installed in image)
set +e
source /opt/openfoam9/etc/bashrc
set -e

echo "=== Environment ==="
echo "FOAM_USER_LIBBIN=$FOAM_USER_LIBBIN"
echo "FOAM_USER_APPBIN=$FOAM_USER_APPBIN"
echo "PATH includes OF: $(echo $PATH | tr ':' '\\n' | grep -i foam | head -3)"

# Verify solver is available
echo "=== Checking pre-compiled solver ==="
which detonationFoam_V2.0 || true
ls $FOAM_USER_LIBBIN/lib*.so 2>/dev/null || echo "No user libs in FOAM_USER_LIBBIN"

# Check if solver is in image's compiled location
if ! which detonationFoam_V2.0 >/dev/null 2>&1; then
    echo "Solver not in PATH, checking image build location..."
    export PATH=$PATH:/root/OpenFOAM/-9/platforms/linux64GccDPInt32Opt/bin
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/root/OpenFOAM/-9/platforms/linux64GccDPInt32Opt/lib
    which detonationFoam_V2.0 || {{ echo "ERROR: detonationFoam_V2.0 not found"; exit 1; }}
fi

echo "=== blockMesh ==="
blockMesh
echo "blockMesh done, exit code: $?"

echo "=== setFields ==="
setFields
echo "setFields done, exit code: $?"

echo "=== Decomposing for {np} processors ==="
decomposePar
echo "decomposePar done, exit code: $?"

echo "=== Checking processor directories ==="
ls -d processor*/ 2>/dev/null || {{ echo "ERROR: No processor directories found!"; exit 1; }}
{amr_extra}
echo "=== Running detonationFoam ==="
export OMPI_ALLOW_RUN_AS_ROOT=1
export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
mpirun -np {np} --oversubscribe detonationFoam_V2.0 -parallel 2>&1

echo "=== Reconstructing ==="
reconstructPar 2>&1

echo "=== Job complete ==="
echo "Date: $(date)"
ls -la
""", encoding="utf-8")

    return input_dir


def submit_job(case_name: str, input_dir: Path, project_id: int,
               machine: str, image: str, max_time: int, disk: int) -> str | None:
    job_config = {
        "job_name": f"detonationFoam-{case_name}",
        "command": "bash run.sh",
        "log_file": "run.log",
        "backward_files": [],
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
        description="Submit detonationFoam jobs to Bohrium (pre-compiled image)"
    )
    parser.add_argument("case", type=Path, help="Path to OpenFOAM case directory")
    parser.add_argument("--np", type=int, default=DEFAULT_NP,
                        help=f"MPI processes (default: {DEFAULT_NP})")
    parser.add_argument("--project-id", type=int, default=0)
    parser.add_argument("--machine", default=DEFAULT_MACHINE,
                        help=f"Machine type (default: {DEFAULT_MACHINE})")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--max-time", type=int, default=DEFAULT_MAX_RUN_TIME)
    parser.add_argument("--disk", type=int, default=DEFAULT_DISK_SIZE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll", action="store_true")
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
    is_amr = (case_dir / "constant" / "dynamicMeshDict").exists()

    print(f"Case       : {case_name}")
    print(f"AMR        : {'yes' if is_amr else 'no'}")
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

    input_dir = prepare_case(case_dir, args.np, tmp_base, is_amr)
    job_id = submit_job(case_name, input_dir, args.project_id,
                        args.machine, args.image, args.max_time, args.disk)

    if job_id:
        print(f"\nSubmitted: Job ID = {job_id}")
        if args.poll:
            poll_jobs([job_id])
    else:
        print("\nSubmission failed.")
        sys.exit(1)


if __name__ == "__main__":
    _load_bohrium_env()
    main()
