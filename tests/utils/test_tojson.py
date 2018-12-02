# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import numpy as np
from caelus.utils import tojson, struct

class Serializable(tojson.JSONSerializer):
    """Test class for JSONSerializer"""

    _json_public_ = "name cases status vector".split()
    _json_mod_map_ = dict(
        conv_val=lambda x: "%12.2f"%x
    )

    def __init__(self):
        self.name = "test_serializer"
        self.cases = ["case%d"%(d+1) for d in range(5)]
        self.status = struct.Struct(
            submitted=True,
            completed=False,
            failed=False
        )
        self.vector = np.arange(10)
        self.conv_val = 1234.87122

def test_json_file():
    assert(Serializable.json_file() == ".serializable.json")

def test_to_json():
    obj = Serializable()
    val = obj.to_json()
    keys = "name cases status vector conv_val".split()
    dtypes = dict(
        name=str,
        cases=list,
        status=struct.Struct,
        vector=np.ndarray,
        conv_val=str)
    assert(list(val.keys()) == keys)
    for key, dtyp in dtypes.items():
        assert(isinstance(val[key], dtyp))

def test_encode():
    obj = Serializable()
    json_obj = obj.encode()
    expected = """{"name": "test_serializer", "cases": ["case1", "case2", "case3", "case4", "case5"], "status": {"submitted": true, "completed": false, "failed": false}, "vector": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "conv_val": "     1234.87"}"""
    assert(json_obj == expected)
