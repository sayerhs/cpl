# -*- coding: utf-8 -*-

"""\
Wrappers for VTK/pyvista
"""

try:
    import vtk as _vtk

    _has_vtk = True
except ImportError:  # pragma: no cover
    _has_vtk = False

try:
    import pyvista as _pyvista

    _has_pyvista = True
except ImportError:  # pragma: no cover
    _has_pyvista = False


def vtk():
    """Return the vtk module"""
    if not _has_vtk:  # pragma: no cover
        raise ModuleNotFoundError("Cannot locate vtk module")
    return _vtk


def pyvista():
    """Return the pyvista module"""
    if not _has_pyvista:  # pragma: no cover
        raise ModuleNotFoundError("Cannot locate pyvista module")
    return _pyvista
