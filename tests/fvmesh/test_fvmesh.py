# -*- coding: utf-8 -*-

import numpy as np
from numpy.testing import assert_allclose

import pytest

from caelus.fvmesh.fvmesh import FVMesh
from caelus.utils import osutils

try:
    import pyvista

    _has_pyvista = True
except ImportError:
    _has_pyvista = False


pytestmark = pytest.mark.skipif(
    _has_pyvista is False, reason="Need vtk/pyvista for fvmesh tests"
)


@pytest.mark.filterwarnings("ignore: `np.bool`")
def test_fvmesh(test_casedir):
    casedir = str(test_casedir)
    mesh = FVMesh(casedir)
    assert mesh.time_index == 0
    assert len(mesh) == 1
    assert mesh[0] == mesh.time
    assert mesh().n_cells == 8
    assert mesh().n_points == 27
    assert mesh().fields.n_fields == 1
    assert mesh().name == "internalMesh"
    assert len(mesh().point_fields) == 1
    assert len(mesh().cell_fields) == 1
    assert "casedir" in repr(mesh)
    assert "casedir" in str(mesh)
    assert "internalMesh" in repr(mesh())
    assert "internalMesh" in str(mesh())

    assert "CELL" in str(mesh().fields.field_loc)
    assert_allclose(mesh().domain.low, [0.0, 0.0, 0.0])
    assert_allclose(mesh().domain.high, [0.1, 0.1, 0.1])

    field_names = mesh().fields.names
    assert 'U' in field_names
    assert "CELL" in repr(mesh().fields)

    U = mesh().fields('U')
    assert U.ndim == 2
    assert U.shape == (8, 3)
    assert_allclose(U.field_min, [1.0, 0.0, 0.0])
    assert_allclose(U.field_max, [1.0, 0.0, 0.0])
    assert_allclose(U.field_mean, [1.0, 0.0, 0.0])

    bdy = mesh.boundary
    assert bdy.n_blocks == 6
    assert "6" in repr(bdy)
    west = bdy['west']
    assert "west" in repr(west)
    assert "west" in str(west)

    mesh.refresh()
