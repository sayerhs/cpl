# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import numpy as np
from numpy.testing import assert_allclose
from caelus.io.parser import CaelusParseError
from caelus.io import dtypes

def test_empty_file(cparse):
    text = """
// only comments no entries

/* Multi-line comment

   line 2
*/
    """
    out = cparse.parse(text)
    assert(not out)

def test_key_value_entries(cparse):
    text = """
application     pisoSolver;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         10;
deltaT          0.005;
writeControl    timeStep;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression true;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

nu             nu  [0 2 -1 0 0 0 0]  1;
    """
    out = cparse.parse(text)
    assert(out.startFrom == "startTime")
    assert(out.timeFormat == "general")
    assert_allclose(out.deltaT, 0.005)
    assert(isinstance(out.nu, dtypes.DimValue))

def test_key_value_entries2(cparse):
    text = """
    default         none;
    laplacian(nuEff,U) Gauss linear corrected;
    laplacian((1|A(U)),p) Gauss linear corrected;
    laplacian(DkEff,k) Gauss linear corrected;
    laplacian(DepsilonEff,epsilon) Gauss linear corrected;
    laplacian(DREff,R) Gauss linear corrected;
    laplacian(DnuTildaEff,nuTilda) Gauss linear corrected;
    """
    out = cparse.parse(text)
    assert(isinstance(out["laplacian(nuEff,U)"], dtypes.MultipleValues))
    assert(out.default == "none")

def test_nested_dict(cparse):
    text = """
solvers {
    p {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-06;
        relTol          0.05;
    }
    pFinal {
        $p;
        relTol          0;
    }
    U {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-05;
        relTol          0;
    }
}
PISO {
    nCorrectors     2;
    nNonOrthogonalCorrectors 0;
    pRefCell        0;
    pRefValue       0;
}
    """
    out = cparse.parse(text)
    assert(len(out) == 2)
    assert(out.solvers.p.solver == "PCG")
    assert(out.solvers.U.smoother == "symGaussSeidel")
    assert(isinstance(
        out.solvers.pFinal['macro_000'], dtypes.MacroSubstitution))
    assert(out.solvers.pFinal['macro_000'].value == "$p")
    assert('PISO' in out)

def test_uniform_field(cparse):
    text = """
pressure uniform 1.013e5;
velocity uniform (8.0 0 0);
stress uniform (1 0 0 0 0 0 0 0 0);
symstress uniform (1 0 0 0 0 0);
    """
    out = cparse.parse(text)
    assert(isinstance(out.velocity.value, np.ndarray))

def test_nonuniform_field(cparse):
    text = """
velocity nonuniform List<vector> 3
    ( (0 0 0) (1 0 0));
    """
    cparse.parse(text)

def test_field_entries(cparse):
    text = """
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField {
    movingWall {
        type            fixedValue;
        value           $internalField ;
    }
    fixedWalls {
        type            noSlip;
    }
    frontAndBack {
        type            empty;
    }
}
    """
    out = cparse.parse(text)
    assert(len(out) == 3)
    assert(len(out.boundaryField) == 3)
    assert(isinstance(out.dimensions, dtypes.Dimension))
    assert(isinstance(out.internalField, dtypes.Field))
    assert(out.internalField.ftype == "uniform")

def test_macro_expansions(cparse):
    text1 = """
    a 10;
    b $a;
    """
    text2 = """
    subdict
    {
        a 10;
    }
    b $subdict.a;
    """
    text3 = """
    b a;
    c ${${b}}; // returns 10, since $b returns "a", and $a returns 10
    subdict1
    {
        b $..a; // double-dot takes scope up 1 level, then "a" is available
        subsubdict
        {
            c $:a; // colon takes scope to top level, then "a" is available
        }
    }
    """
    out = cparse.parse(text1)
    assert(out.b == "$a")
    out = cparse.parse(text2)
    assert (out.b == "$subdict.a")
    out = cparse.parse(text3)
    assert(out.c == "${${b}}")
    assert(out.subdict1.b == "$..a")
    assert(out.subdict1.subsubdict.c == "$:a")


def test_include_directive(cparse):
    text = """
    #include "initialConditions"
    internalField uniform $pressure;
    boundaryField
    {
        patch1
        {
            type fixedValue;
            value $internalField;
        }
    }
    """
    out = cparse.parse(text)
    assert("directive_000" in out)
    assert(isinstance(out.directive_000, dtypes.Directive))

def test_calc_directive(cparse):
    text = """
    //- Half angle of wedge in degrees
    halfAngle 45.0;
    //- Radius of pipe [m]
    radius 0.5;
    radHalfAngle    #calc "degToRad($halfAngle)";
    y               #calc "$radius*sin($radHalfAngle)";
    minY            #calc "-1.0*$y";
    z               #calc "$radius*cos($radHalfAngle)";
    minZ            #calc "-1.0*$z";
    """
    out = cparse.parse(text)
    assert_allclose(out.halfAngle, 45.0)
    assert(isinstance(out.minY, dtypes.CalcDirective))
    assert(out.minY.value == '"-1.0*$y"')

def test_eval_directive(cparse):
    text = """
    // Allow 10% of time for initialisation before sampling
    timeStart       #eval #{ 0.1 * ${/endTime} #};
    r0CosT          #eval{ $r0*cos(degToRad($t   )) };
    c               #eval "sin(pi()*$a/$b)";

    d  #eval{
        // ignore: sin(pi()*$a/$b)
        sin(degToRad(45))
    };
    """
    out = cparse.parse(text)
    assert(out.r0CosT.value == "{ $r0*cos(degToRad($t   )) }")
    assert(out.d.value.count('\n') == 3)

def test_codestream(cparse):
    text = """
momentOfInertia #codeStream
{
    codeInclude
    #{
        #include ”diagTensor.H”
    #};

    code
    #{
        scalar sqrLx = sqr($Lx);
        scalar sqrLy = sqr($Ly);
        scalar sqrLz = sqr($Lz);
        os  <<
            $mass
           *diagTensor(sqrLy + sqrLz, sqrLx + sqrLz, sqrLx + sqrLy)/12.0;
    #};
};
    """
    out = cparse.parse(text)
    assert(isinstance(out.momentOfInertia, dtypes.CodeStream))
    assert(out.momentOfInertia.directive == "#codeStream")

def test_arrays(cparse):
    text = """
vertices
(
    (0 0 0)
    (1 0 0)
    (1 1 0)
    (0 1 0)
    (0 0 0.1)
    (1 0 0.1)
    (1 1 0.1)
    (0 1 0.1)
);
    """
    vout = np.array(
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
         [0, 0, 0.1], [1, 0, 0.1], [1, 1, 0.1], [0, 1, 0.1],])
    out = cparse.parse(text)
    assert(out.vertices.shape == (8, 3))
    assert_allclose(out.vertices, vout)

def test_lists(cparse):
    text = """
list0 ( ) ;

list1 ( 1.2 2.3 3.4 4.5);

list2 4 ( 1.2 2.3 3.4 4.5);

list3 List<vector> ( 1.0 2.0 3.0 );

list4 List<vector> 4 ( 1.0 2.0 3.0 );

list5 4 ( abc (1 3) 10 value );

list5 List<something> 4 ( abc (1 3) 10 value );

list6 List<something> 4 ( abc 10 value );
    """
    out = cparse.parse(text)
    assert(out.list1.shape == (4,))
    assert(isinstance(out.list4, dtypes.ListTemplate))
    assert(out.list4.value.shape == (3,))

def test_multi_list_entries(cparse):
    text = """
        accept (greater 0.5) and (less 0.1);

        bounds (1 1 1) (2 2 2);

        scale           table
        (
            (0.00   1.0)
            (0.20   1.0)
            (0.30   0.0)
        );
    """
    out = cparse.parse(text)
    assert(all(isinstance(v, dtypes.MultipleValues)
               for v in out.values()))

def test_blockmesh_dict(cparse):
    text = """
    edges (arc 1 5 (1.1 0.0 0.5));
    blocks (
      hex (0 1 2 3 4 5 6 7) (100 300 100)
      simpleGrading
      (
          1                  // x-direction expansion ratio
          (
              (0.2 0.3 4)    // 20% y-dir, 30% cells, expansion = 4
              (0.6 0.4 1)    // 60% y-dir, 40% cells, expansion = 1
              (0.2 0.3 0.25) // 20% y-dir, 30% cells, expansion = 0.25 (1/4)
          )
          3                  // z-direction expansion ratio
      )
    );
    boundary               // keyword
    (
        inlet              // patch name
        {
            type patch;    // patch type for patch 0
            faces
            (
                (0 4 7 3)  // block face in this patch
            );
        }                  // end of 0th patch definition
        outlet             // patch name
        {
            type patch;    // patch type for patch 1
            faces ((1 2 6 5));
        }
        walls
        {
            type wall;
            faces ((0 1 5 4) (0 3 2 1) (3 7 6 2) (4 5 6 7));
        }
    );
    """
    out = cparse.parse(text)
    assert(isinstance(out.edges, list))
    assert(len(out.edges) == 4)

def test_boundary_file(cparse):
    text = """
FoamFile {
    version     2.0;
    format      ascii;
    class       polyBoundaryMesh;
    location    "constant/polyMesh";
    object      boundary;
}

3 (
    movingWall
    {
        type            wall;
        nFaces          20;
        startFace       760;
    }
    fixedWalls
    {
        type            wall;
        nFaces          60;
        startFace       780;
    }
    frontAndBack
    {
        type            empty;
        nFaces          800;
        startFace       840;
    })
    """
    out = cparse.parse(text)
    assert("boundary" in out)
    assert(len(out.boundary.value) == 3)

def test_facelist_file(cparse):
    text = """
FoamFile
{
    version     2.0;
    format      ascii;
    class       faceList;
    location    "constant/polyMesh";
    object      faces;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //


7
(
4(1 22 463 442)
4(21 462 463 22)
4(2 23 464 443)
4(22 463 464 23)
4(3 24 465 444)
4(23 464 465 24)
4(4 25 466 445))
    """
    out = cparse.parse(text)
    assert("face_list" in out)

def test_function_objects(cparse):
    text = """
functions {
    readFields {
        functionObjectLibs (fieldFunctionObjects);
        type            readFields; fields          (p U);
    }
    streamLines {
        type            streamLine;
        outputControl   outputTime;
        setFormat       vtk;
        UName            U;
        trackForward    true;
        fields          ( p U );
        lifeTime        10000;
        nSubCycle       5;
        cloudName       particleTracks;
        seedSampleSet   uniform;
        uniformCoeffs {
            type            uniform; axis            x;
            start           ( -1.001 1e-07 0.0011 );
            end             ( -1.001 1e-07 1.0011 );
            nPoints         20;
        }
    }
    cuttingPlane {
        type            surfaces;
        functionObjectLibs ( "libsampling.so" );
        outputControl   outputTime;
        surfaceFormat   vtk;
        fields          ( p U );
        interpolationScheme cellPoint;
        surfaces        ( yNormal { type cuttingPlane ; planeType pointAndNormal ; pointAndNormalDict { basePoint ( 0 0 0 ) ; normalVector ( 0 1 0 ) ; } interpolate true ; } );
    }
    forces
    {
        type            forceCoeffs;
        functionObjectLibs ( "libforces.so" );
        outputControl   timeStep;
        outputInterval  1;
        patches         ( "motorBike.*" );
        pName           p; UName           U; rhoName         rhoInf;
        log             true; rhoInf          1;
        liftDir         ( 0 0 1 );
        dragDir         ( 1 0 0 );
        CofR            ( 0.72 0 0 );
        pitchAxis       ( 0 1 0 );
        magUInf         20; lRef            1.42; Aref            0.75;
    }
    // Create additional volume fields (for sampling)
    derivedFields
    {
        // Mandatory entries
        type            derivedFields;
        libs            (fieldFunctionObjects);
        derived         (rhoU pTotal);

        // Optional entries
        rhoRef          1.25;

        // Optional (inherited) entries
        region          region0;
        enabled         true;
        log             true;
        timeStart       0;
        timeEnd         10000;
        executeControl  timeStep;
        executeInterval 1;
        writeControl    none;
        writeInterval  -1;
    }
}
    """
    out = cparse.parse(text)
    assert(len(out.functions) == 5)
    assert(len(out.functions.cuttingPlane.surfaces) == 1)

def test_surface_interpolate(cparse):
    text = """
surfaceInterpolate1
{
    // Mandatory entries
    type            surfaceInterpolate;
    libs            (fieldFunctionObjects);
    fields          ((U surfaceU) (p surfaceP) (k surfaceK) (divU surfaceDivU));

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  writeTime;
    executeInterval -1;
    writeControl    writeTime;
    writeInterval   -1;
}
    """
    out = cparse.parse(text)
    assert(len(out) == 1)
    fields = out.surfaceInterpolate1.fields
    assert(len(fields) == 4)

def test_failure_dict(cparse):
    text = """ {
    default         none;
    laplacian(nuEff,U) Gauss linear corrected;
    laplacian((1|A(U)),p) Gauss linear corrected;
    laplacian(DkEff,k) Gauss linear corrected;
    laplacian(DepsilonEff,epsilon) Gauss linear corrected;
    laplacian(DREff,R) Gauss linear corrected;
    laplacian(DnuTildaEff,nuTilda) Gauss linear corrected;
}
    """
    # Fail with missing keyword
    with pytest.raises(CaelusParseError):
        cparse.parse(text)

def test_missing_semi(cparse):
    text = """
    line1 Gauss linear NO_SEMI
    """
    with pytest.raises(CaelusParseError):
        cparse.parse(text)

def test_unmatched_codeblock(cparse):
    text = """
    #{
        double time = 0.0;
        double end_time = time + 1000.0;
    """
    with pytest.raises(CaelusParseError):
        cparse.parse(text)
