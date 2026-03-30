# Paper Reproduction — detonationFoam

## Overview

Systematic reproduction of 27 published papers (2022-2026) that used the detonationFoam solver. Modeled after the [asurf paper reproduction system](https://github.com/tianhanz/asurf).

- **27 papers catalogued** with tier classification and WTS difficulty scores
- **5-phase workflow**: Preparation → Parameter extraction → Independent reference → Target computation → Comparison
- **Structured tracking** via per-paper `meta.yaml` and `trace.md`

## Status Summary

| Status | Count |
|--------|-------|
| NOT_STARTED | 27 |
| IN_PROGRESS | 0 |
| PARTIAL | 0 |
| COMPLETE | 0 |
| BLOCKED | 0 |
| UNREPRODUCIBLE | 0 |

Run `python3 papers/tools/status.py` for the live status table.

## Tier Classification

| Tier | Count | Description | Estimated effort |
|------|-------|-------------|-----------------|
| **A** | 5 | Stock solver + H2/O2 + simple geometry | 1-3 days each |
| **B** | 5 | Stock solver + new mechanism needed | 1-2 weeks each |
| **C** | 14 | Stock solver + complex geometry/mesh | 2-4 weeks each |
| **D** | 3 | Needs solver modifications (RDE, scramjet) | 2-4 weeks each |

## Paper Index

### Tier A — Stock solver + H2/O2 mechanism

| # | Paper | Dim | Phenomenon | Status |
|---|-------|-----|------------|--------|
| [2] | [Sun 2023 CPC 292](sun-2023-cpc-292/) | 1D/2D | Solver paper — CJ detonation + cellular structure | NOT_STARTED |
| [7] | [Sun 2024 pci-40](sun-2024-pci-40/) | 1D/2D | Detonation initiation by multiple hot spots | NOT_STARTED |
| [11] | [Sun 2025 JFM 1010](sun-2025-jfm-1010/) | 1D/2D | Dual hot-spot initiation | NOT_STARTED |
| [17] | [Sun 2025 JFM 1022](sun-2025-jfm-1022/) | 2D | Cellular detonation bifurcation (two-stage) | NOT_STARTED |
| [21] | [Li 2026 aa-240](li-2026-aa-240/) | 2D | Unreacted pocket closure + jet flame | NOT_STARTED |

### Tier B — New mechanism needed

| # | Paper | Dim | Fuel | Mechanism needed | Status |
|---|-------|-----|------|-----------------|--------|
| [16] | [Sun 2025 pci-41](sun-2025-pci-41/) | 1D | Cracked NH3 | NH3/H2/air (extended) | NOT_STARTED |
| [14] | [Sun 2025 cf-281](sun-2025-cf-281/) | 1D/2D | Cracked NH3/air | NH3/H2/air (extended) | NOT_STARTED |
| [6] | [Liu 2024 ijhe-86](liu-2024-ijhe-86/) | 2D | NH3/H2/air | NH3/H2/air (Stagni/Song) | NOT_STARTED |
| [13] | [Liu 2025 pof-37](liu-2025-pof-37/) | 2D | n-C12H26/air | Reduced n-dodecane | NOT_STARTED |
| [20] | [Dahake 2026 cf-285](dahake-2026-cf-285/) | 1D/2D | C2H4/O2/O3 | Ethylene-ozone | NOT_STARTED |

### Tier C — Complex geometry / mesh engineering

| # | Paper | Dim | Geometry type | Status |
|---|-------|-----|---------------|--------|
| [1] | [Sun 2022 pof-34](sun-2022-pof-34/) | 2D | Wedge-angle change (ODW) | NOT_STARTED |
| [3] | [Sun 2023 aiaaj-61](sun-2023-aiaaj-61/) | 2D | Unsteady inflow ODW | NOT_STARTED |
| [10] | [Sun 2025 cf-271](sun-2025-cf-271/) | 2D | ODW + boundary layer (NS) | NOT_STARTED |
| [19] | [Yuan 2026 ast-170](yuan-2026-ast-170/) | 2D | Wedge rotation ODW (confined) | NOT_STARTED |
| [26] | [Yuan 2026 pe-2](yuan-2026-pe-2/) | 2D | Jet + ODW (confined) | NOT_STARTED |
| [8] | [Yang 2024 cf-270](yang-2024-cf-270/) | 2D | Detonation reflection | NOT_STARTED |
| [9] | [Yang 2024 pci-40](yang-2024-pci-40/) | 2D | Cellular detonation reflection | NOT_STARTED |
| [12] | [Yang 2025 cja](yang-2025-cja/) | 2D | DDT onset modes | NOT_STARTED |
| [22] | [Cheng 2026 cf-284](cheng-2026-cf-284/) | 2D | Variable-section channel | NOT_STARTED |
| [25] | [Wang 2026 fme-12](wang-2026-fme-12/) | 2D/3D | Double-bend duct | NOT_STARTED |
| [4] | [Hu 2024 ast-150](hu-2024-ast-150/) | 2D/3D | Detonation diffraction | NOT_STARTED |
| [23] | [Cao 2026 cf-283](cao-2026-cf-283/) | 2D | Diffraction w/ rounded corner | NOT_STARTED |
| [27] | [Sun 2026 prf](sun-2026-prf/) | 2D | Obstacle arrays (FA + detonation) | NOT_STARTED |
| [24] | [Euteneuer 2026 aiaa](euteneuer-2026-aiaa/) | 3D | 3D oblique detonation | NOT_STARTED |

### Tier D — Solver modifications needed

| # | Paper | Dim | Challenge | Status |
|---|-------|-----|-----------|--------|
| [5] | [Hu 2024 ate-255](hu-2024-ate-255/) | 2D/3D | Linear RDE — injection BCs | NOT_STARTED |
| [15] | [Hu 2025 ast-168](hu-2025-ast-168/) | 2D/3D | RDE propulsion performance | NOT_STARTED |
| [18] | [Li 2025 aiaaj](li-2025-aiaaj/) | 2D/3D | Scramjet dual combustion zone | NOT_STARTED |

## Key Documents

- [TOOL_REGISTRY.md](TOOL_REGISTRY.md) — Available mechanisms, solver modes, compute resources
- [WTS_RUBRIC.md](WTS_RUBRIC.md) — Work-To-Score difficulty rubric

## Execution Order

1. **Paper [2]** (Sun 2023 CPC) — sentinel case, validates the pipeline
2. **Tier A** remaining — [7], [11], [17], [21]
3. **Tier B** — mechanism sourcing + conversion, then run
4. **Tier C** grouped by geometry (wedge → channel → diffraction → 3D)
5. **Tier D** — assess feasibility, attempt [5]/[15], mark [18] UNREPRODUCIBLE
