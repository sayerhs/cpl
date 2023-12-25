# -*- coding: utf-8 -*-
# pylint: disable=unused-import, function-redefined

"""\
Pythonic-wrappers to VTK data structures
-----------------------------------------

This module extends pyvista wrappers to provide OpenFOAM specific
methods/properties.
"""

try:
    from ._helpers import wrap

    _has_pyvista = True
except ImportError:  # pragma: no cover
    _has_pyvista = False

if not _has_pyvista:  # pragma: no cover

    def wrap(*args, **kwargs):  # noqa: F811
        """Helper function"""
        raise NotImplementedError("Please install VTK/pyvista")
