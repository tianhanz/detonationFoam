#!/usr/bin/env python3
"""Scan all papers/*/meta.yaml and print a status table."""

import sys
from pathlib import Path

import yaml

PAPERS_DIR = Path(__file__).resolve().parent.parent
STATUS_ORDER = [
    "COMPLETE",
    "IN_PROGRESS",
    "PARTIAL",
    "NOT_STARTED",
    "BLOCKED",
    "UNREPRODUCIBLE",
]


def load_papers():
    papers = []
    for meta_path in sorted(PAPERS_DIR.glob("*/meta.yaml")):
        with open(meta_path) as f:
            meta = yaml.safe_load(f) or {}
        paper_id = meta_path.parent.name
        papers.append(
            {
                "id": paper_id,
                "status": meta.get("status", "NOT_STARTED"),
                "tier": meta.get("tier", "?"),
                "wts": meta.get("wts_score", 0),
                "fuel": meta.get("fuel", ""),
                "dim": meta.get("dimensions", ""),
                "figs_done": meta.get("figures_done", 0),
                "figs_total": meta.get("figures_total", 0),
                "phase": meta.get("phase", "—"),
                "mechanism": (meta.get("mechanism", "") or "")[:30],
            }
        )
    return papers


def print_table(papers):
    # Header
    fmt = "{:<35s} {:>4s} {:>4s} {:>3s} {:>6s} {:>5s} {:>5s} {:<12s}"
    header = fmt.format("Paper", "Tier", "WTS", "Dim", "Figs", "Phase", "Stat", "Fuel")
    print(header)
    print("-" * len(header))

    for p in papers:
        figs = f"{p['figs_done']}/{p['figs_total']}" if p["figs_total"] else "—"
        status_short = p["status"][:11]
        phase = str(p["phase"]) if p["phase"] is not None else "—"
        print(
            fmt.format(
                p["id"][:35],
                p["tier"],
                str(p["wts"]),
                p["dim"],
                figs,
                phase,
                status_short,
                p["fuel"][:12],
            )
        )


def print_summary(papers):
    counts = {}
    for p in papers:
        counts[p["status"]] = counts.get(p["status"], 0) + 1

    print(f"\nTotal: {len(papers)} papers")
    for status in STATUS_ORDER:
        if status in counts:
            print(f"  {status}: {counts[status]}")


def main():
    papers = load_papers()
    if not papers:
        print("No papers found. Run create_paper.py to scaffold paper directories.")
        sys.exit(0)

    print_table(papers)
    print_summary(papers)


if __name__ == "__main__":
    main()
