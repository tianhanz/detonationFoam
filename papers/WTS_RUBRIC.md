# Work-To-Score (WTS) Difficulty Rubric

Adapted from the asurf project for detonationFoam paper reproduction.

## Gate: Solver Feasibility (D0)

Applied first — binary gate before scoring.

| Gate | Meaning | Action |
|------|---------|--------|
| **PASS** | Paper's key results use detonationFoam or equivalent density-based solver | Proceed to scoring |
| **PARTIAL** | Some results reproducible, others need capabilities we lack | Score reproducible subset |
| **FAIL** | Results need LES, turbulence models, or fundamentally different solver | Mark UNREPRODUCIBLE |

## Scored Dimensions (D1-D6)

Each scored 1-5. Higher = harder.

### D1: Information Completeness (weight: 2x)

| Score | Criterion |
|-------|-----------|
| 1 | All parameters explicitly stated (mesh, IC, BC, mechanism, endTime) |
| 2 | Most parameters stated, 1-2 need inference from context |
| 3 | Several parameters missing, must read related papers |
| 4 | Key parameters ambiguous, multiple interpretations possible |
| 5 | Custom/unpublished mechanism or proprietary setup |

### D2: Physics Complexity (weight: 3x)

| Score | Criterion |
|-------|-----------|
| 1 | 1D detonation propagation (CJ velocity, pressure profile) |
| 2 | 2D detonation in simple geometry (channel, cellular structure) |
| 3 | 2D with non-trivial physics (ODW, reflection, diffraction) |
| 4 | 2D with coupled physics (viscous BL + detonation, DDT) |
| 5 | 3D detonation, rotating detonation, multi-physics coupling |

### D3: Chemical Mechanism Complexity (weight: 1x)

| Score | Criterion |
|-------|-----------|
| 1 | H2/O2 (11 species) — mechanism in repo |
| 2 | NH3 (33 species) — mechanism in repo |
| 3 | Small hydrocarbon (C1-C2, ~30-50 species) — needs sourcing |
| 4 | Large hydrocarbon (C3+, 50-100 species) — needs reduction |
| 5 | Custom mechanism (200+ species or unpublished) |

### D4: Computational Cost (weight: 2x)

| Score | Criterion |
|-------|-----------|
| 1 | < 100 core-hours (1D, short domain) |
| 2 | 100-500 core-hours (2D small, or 1D long) |
| 3 | 500-2000 core-hours (2D medium, cellular structure) |
| 4 | 2000-10000 core-hours (2D large, fine resolution) |
| 5 | > 10000 core-hours (3D, or very large 2D) |

### D5: Post-Processing Complexity (weight: 1x)

| Score | Criterion |
|-------|-----------|
| 1 | Scalar extraction (CJ velocity, pressure peak) |
| 2 | 1D profiles (x-t diagram, ZND structure) |
| 3 | 2D contour plots (pressure, temperature, species) |
| 4 | Derived quantities (cell size measurement, soot foil, frequency analysis) |
| 5 | Complex analysis (3D iso-surfaces, spectral decomposition, statistical) |

### D6: Mesh/Setup Engineering (weight: 3x)

| Score | Criterion |
|-------|-----------|
| 1 | Existing case in repo, minimal changes (IC/BC only) |
| 2 | Simple blockMesh modification (domain size, resolution) |
| 3 | Custom blockMesh (wedge, channel with features) |
| 4 | Complex mesh (obstacles, bends, moving boundaries) |
| 5 | 3D mesh or needs solver code modifications |

## Formula

```
WTS = 2*D1 + 3*D2 + 1*D3 + 2*D4 + 1*D5 + 3*D6
```

- **Minimum**: 12 (all 1s)
- **Maximum**: 60 (all 5s)

## Decision Thresholds

| WTS | Category | Expected timeline |
|-----|----------|-------------------|
| 12-18 | Straightforward | 1-3 days |
| 19-28 | Moderate | 1-2 weeks |
| 29-38 | Challenging | 2-4 weeks |
| 39-48 | Very Hard | 1-2 months |
| 49-60 | Impractical | Defer or mark UNREPRODUCIBLE |

## Automatic Flags

- D2 = 5 → Flag: "3D or multi-physics — assess HPC resources"
- D3 = 5 → Flag: "Mechanism unavailable — check paper supplement"
- D6 = 5 → Flag: "Solver modification needed — assess feasibility first"
