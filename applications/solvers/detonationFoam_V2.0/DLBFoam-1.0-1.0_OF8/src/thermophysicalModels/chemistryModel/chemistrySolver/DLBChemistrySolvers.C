/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | DLBFoam: Dynamic Load Balancing
   \\    /   O peration     | for fast reactive simulations
    \\  /    A nd           |
     \\/     M anipulation  | 2020, Aalto University, Finland
-------------------------------------------------------------------------------
License
    This file is part of DLBFoam library, derived from OpenFOAM.

    https://github.com/blttkgl/DLBFoam

    OpenFOAM is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    OpenFOAM is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.
    You should have received a copy of the GNU General Public License
    along with OpenFOAM.  If not, see <http://www.gnu.org/licenses/>.

\*---------------------------------------------------------------------------*/

#include "noChemistrySolver.H"
#include "EulerImplicit.H"
#include "ode.H"
#include "LoadBalancedChemistryModel.H"

#include "forGases.H"
#include "forLiquids.H"
#include "makeChemistrySolver.H"


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#define defineChemistrySolvers(nullArg, ThermoPhysics)                         \
    defineChemistrySolver                                                      \
    (                                                                          \
        LoadBalancedChemistryModel,                                            \
        ThermoPhysics                                                          \
    );

#define makeChemistrySolvers(Solver, ThermoPhysics)                            \
    makeChemistrySolver                                                        \
    (                                                                          \
        Solver,                                                                \
        LoadBalancedChemistryModel,                                            \
        ThermoPhysics                                                          \
    );

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{
    // gases
    forCoeffGases(defineChemistrySolvers, nullArg);

    forCoeffGases(makeChemistrySolvers, noChemistrySolver);
    forCoeffGases(makeChemistrySolvers, EulerImplicit);
    forCoeffGases(makeChemistrySolvers, ode);

    // liquids
    forCoeffLiquids(defineChemistrySolvers, nullArg);

    forCoeffLiquids(makeChemistrySolvers, noChemistrySolver);
    forCoeffLiquids(makeChemistrySolvers, EulerImplicit);
    forCoeffLiquids(makeChemistrySolvers, ode);
}

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
