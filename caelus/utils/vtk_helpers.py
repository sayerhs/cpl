# -*- coding: utf-8 -*-

"""\
Wrappers for VTK/pyvista
"""

try:
    import vtk as _vtk
    _has_vtk = True
except ImportError:
    _has_vtk = False

try:
    import pyvista as _pyvista
    _has_pyvista = True
except ImportError:
    _has_pyvista = False

def vtk():
    """Return the vtk module"""
    if not _has_vtk:
        raise ModuleNotFoundError("Cannot locate vtk module")
    return _vtk

def pyvista():
    """Return the pyvista module"""
    if not _has_pyvista:
        raise ModuleNotFoundError("Cannot locate pyvista module")
    return _pyvista
