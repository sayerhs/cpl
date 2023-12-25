# -*- coding: utf-8 -*-

"""\
VTK wrappers to represent OpenFOAM fvMesh components
------------------------------------------------------
"""

import numpy as np

import pyvista as pv
import vtk


class Field(pv.pyvista_ndarray):
    """OpenFOAM field.

    Thin-wrapper around ``np.ndarray`` to provide some convenience functions.
    """

    @property
    def field_min(self):
        """Minimum value of the field."""
        return self.min(axis=0)

    @property
    def field_max(self):
        """Maximum value of the field."""
        return self.max(axis=0)

    @property
    def field_mean(self):
        """Mean value of the field"""
        return self.mean(axis=0)


class FieldList:
    """Collection of finite volume fields associated with a mesh."""

    def __init__(self, field_arr):
        self.field_arr = field_arr

    @property
    def field_loc(self):
        """Location of the field (cell or node).

        While OpenFOAM fields are usually declared on cell centers, VTK
        utilities require corresponding point fields to perform sampling
        operations.
        """
        return self.field_arr.association

    @property
    def n_fields(self):
        """Number of fields available"""
        return len(self.field_arr)

    @property
    def names(self):
        return self.field_arr.keys()

    def __len__(self):
        return len(self.field_arr)

    def __getitem__(self, field):
        return np.asarray(self.field_arr[field]).view(Field)

    def __call__(self, field):
        return np.asarray(self.field_arr[field]).view(Field)

    def __repr__(self):
        return "<%s: (%s) %s>" % (
            self.__class__.__name__,
            self.field_arr.association.name,
            self.field_arr.keys(),
        )

    def __str__(self):
        return f"Fields:\n  {self.field_arr.keys()}"


class Domain:
    """Extents of the computational domain."""

    def __init__(self, bounds):
        """
        Args:
            bounds (list-like): Output of GetBounds VTK method
        """
        self._low = np.asarray(bounds[0::2])
        self._high = np.asarray(bounds[1::2])

    @property
    def low(self):
        """Low corner of the bounding box"""
        return self._low

    @property
    def high(self):
        """High corner of the bounding box"""
        return self._high

    @property
    def lengths(self):
        """Lengths of the bounding box"""
        return self.high - self.low

    def __str__(self):
        blen = self.lengths
        dirs = "X Y Z".split()
        return "Domain:\n" + '\n'.join(
            f"  {dirs[i]}: {self.low[i]} - {self.high[i]} ({blen[i]})"
            for i in range(3)
        )


class FoamMixin:
    """OpenFOAM specific methods/properties for VTK/pyvista"""

    @property
    def name(self):
        """Name of this block"""
        return self._blk_name

    @name.setter
    def name(self, blk_name):
        self._blk_name = blk_name

    @property
    def fields(self):
        """OpenFOAM geometric fields.

        Returns the cell-centered fields if available, otherwise returns the
        point fields. Useful when wrapping ``vtk.vtkPolyData`` objects.
        """
        return FieldList(self.cell_data or self.point_data)

    @property
    def point_fields(self):
        """List of fields defined on nodes."""
        return FieldList(self.point_data)

    @property
    def cell_fields(self):
        """List of fields defined on cell centers."""
        return FieldList(self.cell_data)

    @property
    def domain(self):
        """Computational domain."""
        return Domain(self.bounds)


class InternalMesh(pv.UnstructuredGrid, FoamMixin):
    """Representation of OpenFOAM unstructured grid.

    This class contains the representation of the internal mesh and its
    computational fields.
    """

    def __repr__(self):
        return "<%s: %s (%d cells, %d points, %d fields)>" % (
            self.__class__.__name__,
            self.name,
            self.n_cells,
            self.n_points,
            self.fields.n_fields,
        )

    def __str__(self):
        out = f"{self.name} ({self.n_cells} cells, {self.n_points} points, {self.fields.n_fields} fields)\n"
        out += f"{self.domain}"
        if self.fields.n_fields > 0:
            out += f"\n{self.fields}"
        return out


class BoundaryMesh(pv.PolyData, FoamMixin):
    """Representation of the boundary mesh."""

    def __repr__(self):
        return "<%s: %s (%d cells, %d points, %d fields)>" % (
            self.__class__.__name__,
            self.name,
            self.n_cells,
            self.n_points,
            self.fields.n_fields,
        )

    def __str__(self):
        out = f"{self.name} ({self.n_cells} cells, {self.n_points} points, {self.fields.n_fields} fields)\n"
        out += f"{self.domain}"
        if self.fields.n_fields > 0:
            out += f"\n{self.fields}"
        return out


class FoamMultiBlock(pv.MultiBlock, FoamMixin):
    """Representation of OpenFOAM computational mesh blocks.

    This class can represent two things:

      - OpenFOAM computational mesh consisting of an internal mesh and boundary
        patches.
      - List of boundary patches.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for i, name in enumerate(self.keys()):
            self[i].name = name

    def wrap_nested(self):
        """Wrap sub-blocks with Foam specific types"""
        for i in range(self.n_blocks):
            block = self.GetBlock(i)
            if not pv.is_pyvista_dataset(block):
                self.SetBlock(i, wrap(block))

    def __repr__(self):
        return "<%s: %d blocks>" % (self.__class__.__name__, self.n_blocks)

    def __str__(self):
        out = f"{self.__class__.__name__} ({self.n_blocks} blocks)\n"
        out += f"{self.domain}"
        return out


def wrap(obj):
    """Wrap VTK instance in Caelus/pyvista wrapper class.

    See ``pyvista.wrap`` for more details.

    Args:
        obj: dataset to wrap

    Return:
        A wrapped pyvista or Caelus dataset object.
    """
    foam_wrap = {
        'vtkUnstructuredGrid': InternalMesh,
        'vtkPolyData': BoundaryMesh,
        'vtkMultiBlockDataSet': FoamMultiBlock,
    }

    # Wrap OpenFOAM specific types
    if hasattr(obj, 'GetClassName'):
        key = obj.GetClassName()
        return foam_wrap[key](obj) if key in foam_wrap else pv.wrap(obj)

    # Default is to let pyvista decide
    return pv.wrap(obj)  # pragma: no cover
