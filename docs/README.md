# detonationFoam Documentation

Learning materials and reference guides for the detonationFoam solver.

## Quick Reference

- **Solver**: Density-based compressible reacting flow solver for gaseous detonation (OpenFOAM 8)
- **Paper**: Sun et al., Computer Physics Communications 292 (2023) 108859
- **Source**: `applications/solvers/detonationFoam_V2.0/`
- **Tutorial**: `tutorials/1D_NH3_O2_cracking_0.3_detonation/`

## Documents

| Document | Purpose | When to use |
|----------|---------|-------------|
| [learning-path.md](learning-path.md) | 6-level progressive curriculum with checkpoints | Start here; follow levels sequentially |
| [architecture.md](architecture.md) | Solver internals, algorithm flow, class map | Deep-dive into how the code works |
| [config-reference.md](config-reference.md) | Every input file parameter explained | Setting up or modifying a case |
| [simulation-cookbook.md](simulation-cookbook.md) | Step-by-step workflows for common tasks | Running simulations in practice |
| [troubleshooting.md](troubleshooting.md) | Common errors, diagnosis, fixes | When simulations crash or misbehave |

## 3 Solver Types

| Type | Physics | Use when |
|------|---------|----------|
| `Euler` | Inviscid, no diffusion | Fast 1D/2D detonation structure studies |
| `NS_Sutherland` | Viscous, Fick diffusion | General viscous detonation sims |
| `NS_mixtureAverage` | Full multicomponent transport + Soret | Detailed boundary layers, DNS |

## Flux Schemes

`Kurganov` (default, robust) | `HLLC` (sharper shocks) | `HLL` | `HLLCP` | `Tadmor` | `AUSMPlus` | `AUSMPlusUp`

## Key Architectural Insight

V2.0 reconstructs **rhoU (momentum)** at cell faces instead of U (velocity) -- improves scramjet-type simulations. Flux scheme is pluggable via `fvSchemes::fluxScheme`.
