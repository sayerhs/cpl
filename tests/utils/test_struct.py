# -*- coding: utf-8 -*-

"""
caelus.utils.struct Tests
"""

from caelus.utils.struct import Struct

def test_access():
    """Test basic key/attribute access patterns"""
    obj = Struct(a=1, b=2, c=3)
    obj.abc = 10
    obj["xyz"] = 20
    assert obj.a == 1
    assert obj.xyz == 20
    assert obj["abc"] == 10

def test_merge_update():
    """Test dictionary merging"""
    base = Struct(
        LESModel="oneEqEddy",
        delta="bananas",
        printCoeffs="on",
        cubeRootVolCoeffs={
            "deltaCoeff": 1.0,
        },)
    prandtl_coeffs = Struct(
        delta="cubeRootVol",
        smoothCoeffs=dict(
            delta="cubeRootVol",
            maxDeltaRatio=1.1
        ),)

    base.merge(prandtl_coeffs)
    assert base.delta == "cubeRootVol"
    assert "smoothCoeffs" in base
