# -*- coding: utf-8 -*-
# pylint: disable=import-outside-toplevel

"""\
Wrappers for VTK/pyvista
"""


def vtk():
    """Return the vtk module"""
    import vtk as _vtk

    return _vtk


def pyvista():
    """Return the pyvista module"""
    import pyvista as pv

    return pv
