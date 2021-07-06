# -*- coding: utf-8 -*-

import numpy as np
import pytest
from numpy.testing import assert_allclose
from caelus.fvmesh.fvmesh import FVMesh
from caelus.utils import osutils

try:
    import pyvista
    _has_pyvista = True
except ImportError:
    _has_pyvista = False


pytestmark = pytest.mark.skipif(
    _has_pyvista is False,
    reason="Need vtk/pyvista for fvmesh tests")

@pytest.mark.filterwarnings("ignore: `np.bool`")
def test_fvmesh(test_casedir):
    casedir = str(test_casedir)
    mesh = FVMesh(casedir)
    assert(mesh().n_cells == 8)
    assert(mesh().n_points == 27)
    assert(mesh().fields.n_fields == 6)

    assert_allclose(mesh().domain.low, [0.0, 0.0, 0.0])
    assert_allclose(mesh().domain.high, [0.1, 0.1, 0.1])

    field_names = mesh().fields.names
    assert('U' in field_names)

    U = mesh().fields('U')
    assert(U.ndim == 2)
    assert(U.shape == (8, 3))
