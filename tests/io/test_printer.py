# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import os
from caelus.io.printer import foam_writer

def check_text(left, right):
    """Check output for formatting

    Strip trailing whitespaces as they do not matter for indentation and look
    of the file. However, preserve the leading spaces to ensure proper
    indentation in the file.
    """
    for lline, rline in zip(left.splitlines(), right.splitlines()):
        assert(lline.rstrip() == rline.rstrip())

def test_simple_entries(cprinter, cparse):
    expected = """\
application     simpleSolver;

startFrom       latestTime;

startTime       0;

stopAt          endTime;

endTime         200;

deltaT          1;

"""
    out = cparse.parse(expected)
    cprinter(out)
    text = cprinter.buf.getvalue()
    check_text(text, expected)

def test_multi_valued(cprinter, cparse):
    expected = """\
laplacianSchemes
{
    default                            none;
    laplacian(nuEff,U)                 Gauss linear corrected;
    laplacian((1|A(U)),p)              Gauss linear corrected;
    laplacian(DkEff,k)                 Gauss linear corrected;
    laplacian(DepsilonEff,epsilon)     Gauss linear corrected;
    laplacian(DREff,R)                 Gauss linear corrected;
    laplacian(DnuTildaEff,nuTilda)     Gauss linear corrected;
}


"""
    out = cparse.parse(expected)
    cprinter(out)
    text = cprinter.buf.getvalue()
    check_text(text, expected)

def test_arrays(cprinter, cparse):
    expected = """\
convertToMeters     0.1;

vertices
(
    ( 0.   0.   0. )
    ( 1.   0.   0. )
    ( 1.   1.   0. )
    ( 0.   1.   0. )
    ( 0.   0.   0.1)
    ( 1.   0.   0.1)
    ( 1.   1.   0.1)
    ( 0.   1.   0.1)
);

blocks
(
    hex
    (0 1 2 3 4 5 6 7)
    (20 20  1)
    simpleGrading
    (1 1 1)
);

boundary
(
    movingWall
    {
        type      wall;
        faces
        (
            (3 7 6 2)
        );
    }

    fixedWalls
    {
        type      wall;
        faces
        (
            (0 4 7 3)
            (2 6 5 1)
            (1 5 4 0)
        );
    }

    frontAndBack
    {
        type      empty;
        faces
        (
            (0 3 2 1)
            (4 5 6 7)
        );
    }

);
"""
    out = cparse.parse(expected)
    cprinter(out)
    text = cprinter.buf.getvalue()
    check_text(text, expected)

def test_function_objects(cprinter, cparse):
    expected = """\
functions
{
    readFields
    {
        functionObjectLibs     ( "libfieldFunctionObjects.so" );
        type                   readFields;
        fields                 ( p U );
    }

    streamLines
    {
        type              streamLine;
        outputControl     outputTime;
        setFormat         vtk;
        UName             U;
        trackForward      true;
        fields            ( p U );
        lifeTime          10000;
        nSubCycle         5;
        cloudName         particleTracks;
        seedSampleSet     uniform;
        uniformCoeffs
        {
            type        uniform;
            axis        x;
            start       ( -1.00100000e+00   1.00000000e-07   1.10000000e-03);
            end         ( -1.00100000e+00   1.00000000e-07   1.00110000e+00);
            nPoints     20;
        }

    }

    cuttingPlane
    {
        type                    surfaces;
        functionObjectLibs      ( "libsampling.so" );
        outputControl           outputTime;
        surfaceFormat           vtk;
        fields                  ( p U );
        interpolationScheme     cellPoint;
        surfaces
        (
            yNormal
            {
                type                   cuttingPlane;
                planeType              pointAndNormal;
                pointAndNormalDict
                {
                    basePoint        (0 0 0);
                    normalVector     (0 1 0);
                }

                interpolate            true;
            }

        );
    }

    forces
    {
        type                   forceCoeffs;
        functionObjectLibs     ( "libforces.so" );
        outputControl          timeStep;
        outputInterval         1;
        patches                ( "motorBike.*" );
        pName                  p;
        UName                  U;
        rhoName                rhoInf;
        log                    true;
        rhoInf                 1;
        liftDir                (0 0 1);
        dragDir                (1 0 0);
        CofR                   ( 0.72  0.    0.  );
        pitchAxis              (0 1 0);
        magUInf                20;
        lRef                   1.42;
        Aref                   0.75;
    }

}


"""
    out = cparse.parse(expected)
    cprinter(out)
    text = cprinter.buf.getvalue()
    check_text(text, expected)

def test_uniform_fields(cprinter, cparse):
    expected = """\
dimensions        [0 1 -1 0 0 0 0];

internalField     uniform (0 0 0);

boundaryField
{
    movingWall
    {
        type      fixedValue;
        value     uniform (1 0 0);
    }

    fixedWalls
    {
        type     noSlipWall;
    }

    frontAndBack
    {
        type     empty;
    }

}


"""
    out = cparse.parse(expected)
    cprinter(out)
    text = cprinter.buf.getvalue()
    check_text(text, expected)

def test_no_keyword_entries(cprinter, cparse):
    expected = """
#includeEtc "myIncludeFile"


#include "someOtherFile"

solvers
{
    p
    {
        solver             PCG;
        preconditioner     DIC;
        tolerance          1e-06;
        relTol             0.05;
    }

    pFinal
    {
        $p;
        relTol        0;
    }

}


"""
    out = cparse.parse(expected)
    cprinter(out)
    text = cprinter.buf.getvalue()
    check_text(text, expected)

def test_code_objects(cprinter, cparse):
    expected = """\
radHalfAngle        #calc "degToRad($halfAngle)";

y                   #calc "$radius*sin($radHalfAngle)";

minY                #calc "-1.0*$y";

z                   #calc "$radius*cos($radHalfAngle)";

minZ                #calc "-1.0*$z";

momentOfInertia     #codeStream
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
    out = cparse.parse(expected)
    cprinter(out)
    text = cprinter.buf.getvalue()
    check_text(text, expected)


def test_file_write(cparse, tmpdir):
    expected = r"""/*---------------------------------------------------------------------------*\
 * Caelus (http://www.caelus-cml.com)
 *
 * Caelus Python Library (CPL) v0.0.2-50-gb0244da
 * Auto-generated on: 2018-04-08 01:55:07 (UTC)
 *
\*---------------------------------------------------------------------------*/

FoamFile
{
    version      2.0;
    format       ascii;
    class        dictionary;
    location     "system";
    object       controlDict;
}

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleSolver;

startFrom       latestTime;

startTime       0;

stopAt          endTime;

endTime         500;

deltaT          1;

// ************************************************************************* //
"""
    out = cparse.parse(expected)
    header = out.pop("FoamFile")
    outfile = tmpdir.join("controlDict.txt")
    fname = str(outfile)
    with foam_writer(fname, header) as printer:
        printer(out)
    assert(os.path.exists(fname))
    text = outfile.read()
    # Skip the banner because of timestamp and CPL version differences
    idx2 = expected.find("FoamFile")
    idx1 = text.find("FoamFile")
    check_text(text[idx1:], expected[idx2:])
