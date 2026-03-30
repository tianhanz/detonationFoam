#!/usr/bin/env python3
"""Scaffold a new paper directory with meta.yaml, README.md, and trace.md.

Usage:
    python create_paper.py --all          # Create all 27 paper directories
    python create_paper.py sun-2023-cpc-292  # Create a single paper directory
"""

import argparse
import textwrap
from datetime import date
from pathlib import Path

import yaml

PAPERS_DIR = Path(__file__).resolve().parent.parent

# fmt: off
# Complete catalogue of 27 papers using detonationFoam
PAPER_CATALOGUE = [
    # Tier A — Stock solver + H2/O2 mechanism
    {
        "id": "sun-2023-cpc-292",
        "ref_num": 2,
        "authors": "J. Sun, J. Zhu, Z. Chen",
        "title": "detonationFoam: An open-source solver for simulation of gaseous detonation based on OpenFOAM",
        "journal": "Computer Physics Communications",
        "volume": "292",
        "year": 2023,
        "doi": "10.1016/j.cpc.2023.108859",
        "tier": "A",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "1D/2D",
        "geometry": "1D-tube, 2D-channel",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 14,
        "wts_breakdown": {"D1": 1, "D2": 1, "D3": 1, "D4": 2, "D5": 2, "D6": 1},
        "notes": "THE solver paper. Cases already in cases/ directory.",
    },
    {
        "id": "sun-2024-pci-40",
        "ref_num": 7,
        "authors": "J. Sun, Z. Chen, et al.",
        "title": "Numerical study on detonation initiation by multiple hot spots",
        "journal": "Proceedings of the Combustion Institute",
        "volume": "40",
        "year": 2024,
        "doi": "",
        "tier": "A",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "1D/2D",
        "geometry": "1D-tube, 2D-channel",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 18,
        "wts_breakdown": {"D1": 2, "D2": 2, "D3": 1, "D4": 2, "D5": 2, "D6": 1},
        "notes": "Multiple hot-spot initiation. Extends solver paper cases.",
    },
    {
        "id": "sun-2025-jfm-1010",
        "ref_num": 11,
        "authors": "J. Sun, Z. Chen, et al.",
        "title": "Detonation initiation induced by dual hot spots",
        "journal": "Journal of Fluid Mechanics",
        "volume": "1010",
        "year": 2025,
        "doi": "",
        "tier": "A",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "1D/2D",
        "geometry": "1D-tube, 2D-channel",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 20,
        "wts_breakdown": {"D1": 2, "D2": 2, "D3": 1, "D4": 2, "D5": 3, "D6": 1},
        "notes": "Extension of [7] — dual hot-spot initiation, JFM paper.",
    },
    {
        "id": "sun-2025-jfm-1022",
        "ref_num": 17,
        "authors": "J. Sun, Z. Chen",
        "title": "Bifurcation of cellular detonation structure in a mixture with two-stage reactions",
        "journal": "Journal of Fluid Mechanics",
        "volume": "1022",
        "year": 2025,
        "doi": "",
        "tier": "A",
        "fuel": "H2/O2 (diluted)",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-channel",
        "solver_type": "Euler",
        "amr_required": True,
        "wts_score": 24,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 1},
        "notes": "Two-stage behavior via heavy diluent. Needs large 2D domain for cellular bifurcation.",
    },
    {
        "id": "li-2026-aa-240",
        "ref_num": 21,
        "authors": "Y. Li, et al.",
        "title": "Unreacted pocket closure and jet flame formation in H2/O2 detonations with transverse concentration gradients",
        "journal": "Acta Astronautica",
        "volume": "240",
        "year": 2026,
        "doi": "",
        "tier": "A",
        "fuel": "H2/O2",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-channel",
        "solver_type": "Euler",
        "amr_required": True,
        "wts_score": 24,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 1},
        "notes": "Inhomogeneous initial field (concentration gradient). Standard H2/O2.",
    },

    # Tier B — New mechanism needed
    {
        "id": "sun-2025-pci-41",
        "ref_num": 16,
        "authors": "J. Sun, Z. Chen, et al.",
        "title": "Detonation chemistry and propagation characteristics in partially cracked ammonia",
        "journal": "Proceedings of the Combustion Institute",
        "volume": "41",
        "year": 2025,
        "doi": "",
        "tier": "B",
        "fuel": "cracked NH3/air",
        "mechanism": "NH3/H2/air (extended, ~30-60sp)",
        "mechanism_available": False,
        "dimensions": "1D",
        "geometry": "1D-tube",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 22,
        "wts_breakdown": {"D1": 2, "D2": 1, "D3": 3, "D4": 2, "D5": 2, "D6": 1},
        "notes": "1D ammonia cracking detonation. Tutorial has 33sp NH3/O2 — may work.",
    },
    {
        "id": "sun-2025-cf-281",
        "ref_num": 14,
        "authors": "J. Sun, Z. Chen, et al.",
        "title": "Numerical investigation of detonation initiation and propagation in non-uniformly cracked ammonia and air mixtures",
        "journal": "Combustion and Flame",
        "volume": "281",
        "year": 2025,
        "doi": "",
        "tier": "B",
        "fuel": "cracked NH3/air",
        "mechanism": "NH3/H2/air (extended, ~30-60sp)",
        "mechanism_available": False,
        "dimensions": "1D/2D",
        "geometry": "1D-tube, 2D-channel",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 26,
        "wts_breakdown": {"D1": 2, "D2": 2, "D3": 3, "D4": 3, "D5": 2, "D6": 2},
        "notes": "Non-uniform cracking profile. Extension of [16].",
    },
    {
        "id": "liu-2024-ijhe-86",
        "ref_num": 6,
        "authors": "Y. Liu, et al.",
        "title": "Numerical simulations of wedge-induced oblique detonation waves in ammonia/hydrogen/air mixtures",
        "journal": "International Journal of Hydrogen Energy",
        "volume": "86",
        "year": 2024,
        "doi": "",
        "tier": "B",
        "fuel": "NH3/H2/air",
        "mechanism": "NH3/H2/air (Stagni or Song, ~30-60sp)",
        "mechanism_available": False,
        "dimensions": "2D",
        "geometry": "2D-wedge",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 28,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 3, "D4": 3, "D5": 2, "D6": 2},
        "notes": "ODW with ammonia-hydrogen. Needs both mechanism + wedge mesh.",
    },
    {
        "id": "liu-2025-pof-37",
        "ref_num": 13,
        "authors": "Y. Liu, et al.",
        "title": "Numerical study of wedge-induced oblique detonation waves in homogeneous and inhomogeneous n-dodecane/air mixtures",
        "journal": "Physics of Fluids",
        "volume": "37",
        "year": 2025,
        "doi": "",
        "tier": "B",
        "fuel": "n-C12H26/air",
        "mechanism": "Reduced n-dodecane (~30-55sp)",
        "mechanism_available": False,
        "dimensions": "2D",
        "geometry": "2D-wedge",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 32,
        "wts_breakdown": {"D1": 3, "D2": 3, "D3": 4, "D4": 3, "D5": 2, "D6": 2},
        "notes": "Large mechanism + wedge geometry. Inhomogeneous variant adds complexity.",
    },
    {
        "id": "dahake-2026-cf-285",
        "ref_num": 20,
        "authors": "A. Dahake, et al.",
        "title": "Investigating the effect of ozonolysis on the structure and dynamics of ethylene-oxygen-ozone detonations",
        "journal": "Combustion and Flame",
        "volume": "285",
        "year": 2026,
        "doi": "",
        "tier": "B",
        "fuel": "C2H4/O2/O3",
        "mechanism": "Ethylene-ozone (~30-50sp)",
        "mechanism_available": False,
        "dimensions": "1D/2D",
        "geometry": "1D-tube, 2D-channel",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 28,
        "wts_breakdown": {"D1": 3, "D2": 2, "D3": 3, "D4": 2, "D5": 3, "D6": 2},
        "notes": "Ozone chemistry needs sourcing. Unique C2H4/O3 mechanism.",
    },

    # Tier C — Complex geometry / mesh engineering
    {
        "id": "sun-2022-pof-34",
        "ref_num": 1,
        "authors": "J. Sun, Z. Chen, et al.",
        "title": "Effects of wedge-angle change on the evolution of oblique detonation wave structure",
        "journal": "Physics of Fluids",
        "volume": "34",
        "year": 2022,
        "doi": "",
        "tier": "C",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-wedge (variable angle)",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 28,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 3},
        "notes": "Time-varying wedge angle — may need mesh sequence or dynamic mesh.",
    },
    {
        "id": "sun-2023-aiaaj-61",
        "ref_num": 3,
        "authors": "J. Sun, Z. Chen, et al.",
        "title": "Evolution and Control of Oblique Detonation Wave Structure in Unsteady Inflow",
        "journal": "AIAA Journal",
        "volume": "61",
        "year": 2023,
        "doi": "",
        "tier": "C",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-wedge (unsteady inflow)",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 28,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 3},
        "notes": "Unsteady inflow BC on wedge. Needs time-varying BC implementation.",
    },
    {
        "id": "sun-2025-cf-271",
        "ref_num": 10,
        "authors": "J. Sun, Z. Chen, et al.",
        "title": "Dynamic interaction patterns of oblique detonation waves with boundary layers in hypersonic reactive flows",
        "journal": "Combustion and Flame",
        "volume": "271",
        "year": 2025,
        "doi": "",
        "tier": "C",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-wedge (NS, boundary layer)",
        "solver_type": "NS_Sutherland",
        "amr_required": False,
        "wts_score": 32,
        "wts_breakdown": {"D1": 2, "D2": 4, "D3": 1, "D4": 3, "D5": 3, "D6": 3},
        "notes": "Viscous ODW. Requires NS solver + fine near-wall mesh for BL resolution.",
    },
    {
        "id": "yuan-2026-ast-170",
        "ref_num": 19,
        "authors": "X. Yuan, T. Jin",
        "title": "Dynamic response of the unstable oblique detonation wave in confined space via different wedge rotation",
        "journal": "Aerospace Science and Technology",
        "volume": "170",
        "year": 2026,
        "doi": "",
        "tier": "C",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-wedge (rotating, confined)",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 32,
        "wts_breakdown": {"D1": 3, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 4},
        "notes": "Rotating wedge in confined space. Moving mesh or parametric sweep.",
    },
    {
        "id": "yuan-2026-pe-2",
        "ref_num": 26,
        "authors": "X. Yuan, T. Jin",
        "title": "Numerical study on the influence of jet on the stability of oblique detonation waves in confined space",
        "journal": "Propulsion and Energy",
        "volume": "2",
        "year": 2026,
        "doi": "",
        "tier": "C",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-confined (jet + ODW)",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 30,
        "wts_breakdown": {"D1": 3, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 3},
        "notes": "Jet injection interacting with ODW. Custom inlet BC.",
    },
    {
        "id": "yang-2024-cf-270",
        "ref_num": 8,
        "authors": "Z. Yang, B. Zhang",
        "title": "Investigation on the dynamics of shock wave generated by detonation reflection",
        "journal": "Combustion and Flame",
        "volume": "270",
        "year": 2024,
        "doi": "",
        "tier": "C",
        "fuel": "H2/O2",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-channel (reflection wall)",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 26,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 2},
        "notes": "Detonation reflection off a wall. Straightforward channel geometry.",
    },
    {
        "id": "yang-2024-pci-40",
        "ref_num": 9,
        "authors": "Z. Yang, B. Zhang, et al.",
        "title": "Experimental observations of gaseous cellular detonation reflection",
        "journal": "Proceedings of the Combustion Institute",
        "volume": "40",
        "year": 2024,
        "doi": "",
        "tier": "C",
        "fuel": "H2/O2",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-channel (reflection, experimental comparison)",
        "solver_type": "Euler",
        "amr_required": True,
        "wts_score": 28,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 3},
        "notes": "Cellular detonation reflection with experimental comparison. Needs AMR for cell resolution.",
    },
    {
        "id": "yang-2025-cja",
        "ref_num": 12,
        "authors": "Z. Yang, B. Zhang",
        "title": "Typical onset modes of DDT and behavior of strong transverse shocks",
        "journal": "Chinese Journal of Aeronautics",
        "volume": "",
        "year": 2025,
        "doi": "",
        "tier": "C",
        "fuel": "H2/O2",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-channel (DDT, obstacles)",
        "solver_type": "Euler",
        "amr_required": True,
        "wts_score": 32,
        "wts_breakdown": {"D1": 3, "D2": 4, "D3": 1, "D4": 3, "D5": 3, "D6": 3},
        "notes": "DDT is complex multi-regime physics. Needs obstacle geometry + AMR.",
    },
    {
        "id": "cheng-2026-cf-284",
        "ref_num": 22,
        "authors": "J. Cheng, et al.",
        "title": "Dynamics of detonation propagation in a wedged variable-section channel",
        "journal": "Combustion and Flame",
        "volume": "284",
        "year": 2026,
        "doi": "",
        "tier": "C",
        "fuel": "H2/O2",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-channel (variable cross-section)",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 28,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 3},
        "notes": "Expanding/contracting channel with wedge features.",
    },
    {
        "id": "wang-2026-fme-12",
        "ref_num": 25,
        "authors": "Y. Wang, et al.",
        "title": "Propagation characteristics of H2-air detonations in double-bend ducts",
        "journal": "Frontiers in Mechanical Engineering",
        "volume": "12",
        "year": 2026,
        "doi": "",
        "tier": "C",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-duct (double bend)",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 30,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 4},
        "notes": "Complex duct geometry with two bends. Possibly 3D.",
    },
    {
        "id": "hu-2024-ast-150",
        "ref_num": 4,
        "authors": "J. Hu, B. Zhang, et al.",
        "title": "The diffraction and re-initiation characteristics of gaseous detonations with an irregular cellular structure",
        "journal": "Aerospace Science and Technology",
        "volume": "150",
        "year": 2024,
        "doi": "",
        "tier": "C",
        "fuel": "H2/O2",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-expansion (diffraction)",
        "solver_type": "Euler",
        "amr_required": True,
        "wts_score": 30,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 4, "D6": 3},
        "notes": "Detonation diffraction into expansion. Irregular cellular structure analysis.",
    },
    {
        "id": "cao-2026-cf-283",
        "ref_num": 23,
        "authors": "D. Cao, et al.",
        "title": "Detonation diffraction in expansion channels with rounded corner",
        "journal": "Combustion and Flame",
        "volume": "283",
        "year": 2026,
        "doi": "",
        "tier": "C",
        "fuel": "H2/O2",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-expansion (rounded corner)",
        "solver_type": "Euler",
        "amr_required": True,
        "wts_score": 30,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 4},
        "notes": "Curved geometry at expansion corner. Needs snappyHexMesh or blockMesh with arcs.",
    },
    {
        "id": "sun-2026-prf",
        "ref_num": 27,
        "authors": "J. Sun, et al.",
        "title": "Numerical investigation on detonation attenuation and flame acceleration in channels with obstacle arrays",
        "journal": "Physical Review Fluids",
        "volume": "",
        "year": 2026,
        "doi": "",
        "tier": "C",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "2D-channel (obstacle arrays)",
        "solver_type": "Euler",
        "amr_required": True,
        "wts_score": 32,
        "wts_breakdown": {"D1": 2, "D2": 3, "D3": 1, "D4": 3, "D5": 3, "D6": 4},
        "notes": "Obstacle arrays require repeated blockage geometry. FA + DDT physics.",
    },
    {
        "id": "euteneuer-2026-aiaa",
        "ref_num": 24,
        "authors": "C. Euteneuer, et al.",
        "title": "Three-dimensional structures of H2/air oblique detonation waves",
        "journal": "AIAA SCITECH 2026",
        "volume": "",
        "year": 2026,
        "doi": "",
        "tier": "C",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "3D",
        "geometry": "3D-wedge",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 40,
        "wts_breakdown": {"D1": 3, "D2": 5, "D3": 1, "D4": 5, "D5": 4, "D6": 3},
        "notes": "Only 3D paper. Extreme compute cost. No 3D AMR bundled.",
    },

    # Tier D — Solver modifications needed
    {
        "id": "hu-2024-ate-255",
        "ref_num": 5,
        "authors": "J. Hu, B. Zhang",
        "title": "Time/frequency domain analysis of detonation wave propagation in a linear rotating detonation combustor",
        "journal": "Applied Thermal Engineering",
        "volume": "255",
        "year": 2024,
        "doi": "",
        "tier": "D",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D",
        "geometry": "RDE (linear unwrapped)",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 38,
        "wts_breakdown": {"D1": 3, "D2": 4, "D3": 1, "D4": 3, "D5": 4, "D6": 5},
        "notes": "RDE needs injection BCs, periodic azimuthal domain. Major setup work.",
    },
    {
        "id": "hu-2025-ast-168",
        "ref_num": 15,
        "authors": "J. Hu, B. Zhang",
        "title": "Propulsion performance and detonation wave dynamics in a rotating detonation combustor",
        "journal": "Aerospace Science and Technology",
        "volume": "168",
        "year": 2025,
        "doi": "",
        "tier": "D",
        "fuel": "H2/air",
        "mechanism": "Burke 2011 H2/O2 11sp/27rxn",
        "mechanism_available": True,
        "dimensions": "2D/3D",
        "geometry": "RDE (annular)",
        "solver_type": "Euler",
        "amr_required": False,
        "wts_score": 42,
        "wts_breakdown": {"D1": 3, "D2": 5, "D3": 1, "D4": 4, "D5": 4, "D6": 5},
        "notes": "Annular RDE with propulsion metrics. Same as [5] but more complex.",
    },
    {
        "id": "li-2025-aiaaj",
        "ref_num": 18,
        "authors": "M. Li, et al.",
        "title": "Ignition dynamics of a supersonic combustor with parallel dual combustion zones",
        "journal": "AIAA Journal",
        "volume": "",
        "year": 2025,
        "doi": "",
        "tier": "D",
        "fuel": "hydrocarbon/air",
        "mechanism": "unknown",
        "mechanism_available": False,
        "dimensions": "2D/3D",
        "geometry": "scramjet dual-zone",
        "solver_type": "NS_mixtureAverage",
        "amr_required": False,
        "wts_score": 50,
        "wts_breakdown": {"D1": 4, "D2": 5, "D3": 4, "D4": 5, "D5": 4, "D6": 5},
        "notes": "Scramjet combustor — likely needs turbulence model, injection, flameholding. UNREPRODUCIBLE candidate.",
    },
]
# fmt: on


def create_meta_yaml(paper: dict) -> str:
    meta = {
        "status": "NOT_STARTED",
        "tier": paper["tier"],
        "wts_score": paper["wts_score"],
        "wts_breakdown": paper["wts_breakdown"],
        "phase": None,
        "last_updated": str(date.today()),
        "ref_num": paper["ref_num"],
        "authors": paper["authors"],
        "title": paper["title"],
        "journal": paper["journal"],
        "volume": paper["volume"],
        "year": paper["year"],
        "doi": paper["doi"],
        "fuel": paper["fuel"],
        "mechanism": paper["mechanism"],
        "mechanism_available": paper["mechanism_available"],
        "dimensions": paper["dimensions"],
        "geometry": paper["geometry"],
        "solver_type": paper["solver_type"],
        "amr_required": paper["amr_required"],
        "figures_total": 0,
        "figures_done": 0,
        "figures": {},
        "key_result": "",
        "blockers": [],
        "notes": paper["notes"],
    }
    return yaml.dump(meta, default_flow_style=False, sort_keys=False, allow_unicode=True)


def create_readme(paper: dict) -> str:
    return textwrap.dedent(f"""\
    # [{paper['ref_num']}] {paper['authors']} ({paper['year']})

    **{paper['title']}**
    {paper['journal']} {paper['volume']} ({paper['year']})
    {"DOI: " + paper['doi'] if paper['doi'] else "DOI: pending"}

    ## Classification

    | Field | Value |
    |-------|-------|
    | Tier | {paper['tier']} |
    | WTS Score | {paper['wts_score']} |
    | Fuel | {paper['fuel']} |
    | Mechanism | {paper['mechanism']} |
    | Dimensions | {paper['dimensions']} |
    | Geometry | {paper['geometry']} |
    | Solver type | {paper['solver_type']} |
    | AMR required | {'Yes' if paper['amr_required'] else 'No'} |

    ## Figure Index

    | Figure | Description | Status |
    |--------|-------------|--------|
    | — | (populate after reading paper) | — |

    ## Key Results

    (To be filled after reproduction)

    ## Discrepancies

    (Document any deviations from published results)
    """)


def create_trace(paper: dict) -> str:
    today = date.today().isoformat()
    return textwrap.dedent(f"""\
    # Reproduction Trace — {paper['id']}

    ## {today} — Directory scaffolded
    - Paper: {paper['title']}
    - Tier {paper['tier']}, WTS {paper['wts_score']}
    - Status: NOT_STARTED
    """)


def scaffold_paper(paper: dict):
    paper_dir = PAPERS_DIR / paper["id"]
    if paper_dir.exists():
        print(f"  [skip] {paper['id']} already exists")
        return

    paper_dir.mkdir(parents=True)
    for subdir in ("case", "scripts", "figures", "data"):
        (paper_dir / subdir).mkdir()

    (paper_dir / "meta.yaml").write_text(create_meta_yaml(paper))
    (paper_dir / "README.md").write_text(create_readme(paper))
    (paper_dir / "trace.md").write_text(create_trace(paper))
    print(f"  [created] {paper['id']} (Tier {paper['tier']}, WTS {paper['wts_score']})")


def main():
    parser = argparse.ArgumentParser(description="Scaffold paper directories")
    parser.add_argument("paper_id", nargs="?", help="Paper ID to scaffold (or --all)")
    parser.add_argument("--all", action="store_true", help="Scaffold all 27 papers")
    parser.add_argument("--list", action="store_true", help="List all papers in catalogue")
    args = parser.parse_args()

    if args.list:
        for p in PAPER_CATALOGUE:
            print(f"  [{p['ref_num']:>2}] {p['id']:<35s} Tier {p['tier']}  WTS {p['wts_score']:>2}  {p['fuel']}")
        print(f"\nTotal: {len(PAPER_CATALOGUE)} papers")
        return

    if args.all:
        print(f"Scaffolding {len(PAPER_CATALOGUE)} paper directories...")
        for paper in PAPER_CATALOGUE:
            scaffold_paper(paper)
        print(f"\nDone. Run 'python3 papers/tools/status.py' to see status.")
        return

    if args.paper_id:
        match = [p for p in PAPER_CATALOGUE if p["id"] == args.paper_id]
        if not match:
            print(f"Error: paper '{args.paper_id}' not in catalogue.")
            print("Use --list to see available papers, or --all to scaffold all.")
            sys.exit(1)
        scaffold_paper(match[0])
        return

    parser.print_help()


if __name__ == "__main__":
    import sys
    main()
