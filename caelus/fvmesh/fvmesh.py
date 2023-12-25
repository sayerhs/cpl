# -*- coding: utf-8 -*-
# pylint: disable=import-outside-toplevel

"""\
OpenFOAM finite-volume mesh interface
-------------------------------------
"""

import os
import textwrap

import numpy as np

from ..utils import osutils
from . import helpers


class FVMesh:
    """OpenFOAM mesh and solution reader.

    Read OpenFOAM mesh and field data from a case directory. When called
    without arguments, it is assumed that the current working directory is a
    valid OpenFOAM case directory with a mesh. Time directories and fields are
    optional.

    Load data and examine boundary plane information:

    >>> case = FVMesh()
    >>> print("Available times: ", case.available_times)
    >>> print("Current time: ", case.time)

    Print details of internal mesh:

    >>> print(case())

    Access internal fields:

    >>> fields = case().fields
    >>> U = case().fields('U')
    >>> print("Min: ", U.field_min, " Max: ", U.field_max)

    Print information on available boundary patches:

    >>> for bdy in case.boundary:
    ...     print(bdy)

    Loop over available timesteps:

    >>> for time in case:
    ...     print(time, case.get_data_range('epsilon'))

    """

    def __init__(self, casedir=None):
        """
        Args:
            casedir (path): Path to the casedir (default: cwd)
        """
        self.casedir = (
            osutils.abspath(casedir) if casedir is not None else os.getcwd()
        )
        self._ofp = self._load_openfoam()

        # Set data to latest time
        self.time = self.latest_time

    def _load_openfoam(self):
        """Load OpenFOAM case"""
        import vtk

        with osutils.set_work_dir(self.casedir):
            ofp = vtk.vtkOpenFOAMReader()
            ofp.SetFileName("of.foam")
            ofp.SkipZeroTimeOff()
            ofp.Update()
            ofp.EnableAllPatchArrays()
            ofp.Update()
            return ofp

    def refresh(self):
        """Refresh the mesh/output.

        Useful when monitoring a live simulation
        """
        self._ofp = self._load_openfoam()
        self.time = self.latest_time

    @property
    def available_times(self):
        """Return the list of times"""
        import vtk.util.numpy_support as vns

        ofp = self._ofp
        return vns.vtk_to_numpy(ofp.GetTimeValues())

    @property
    def latest_time(self):
        """Latest time available in case directory."""
        return self.available_times[-1]

    @property
    def time(self):
        """Time instance corresponding to the field data."""
        return self._time

    @time.setter
    def time(self, new_time):
        """Update time and corresponding field data."""
        ret = self._ofp.SetTimeValue(new_time)
        if not ret and len(self.available_times) > 1:
            raise ValueError("Invalid time specified: %f" % new_time)
        with osutils.set_work_dir(self.casedir):
            self._ofp.UpdateTimeStep(new_time)
        self._mesh = helpers.wrap(self._ofp.GetOutput())
        self._time = new_time

    @property
    def time_index(self):
        """Time step (integer index)"""
        return np.searchsorted(self.available_times, self.time)

    @property
    def multi_block(self):
        """FOAM base multi-block instance"""
        if not hasattr(self, "_mesh"):
            self._mesh = helpers.wrap(self._ofp.GetOutput())
        return self._mesh

    @property
    def mesh(self):
        """Internal mesh instance."""
        return self._mesh[0]

    @property
    def boundary(self):
        """Boundary mesh instance."""
        if self.multi_block.n_blocks < 2:
            raise ValueError("No boundary field available in mesh")
        return self._mesh[1]

    def __call__(self):
        return self.mesh

    def __len__(self):
        return len(self.available_times)

    def __getitem__(self, i):
        self.time = self.available_times[i]
        return self.time

    def __repr__(self):
        return "<%s: case = %s, time = %.3f>" % (
            self.__class__.__name__,
            self.casedir,
            self.time,
        )

    def __str__(self):
        return (
            textwrap.dedent(
                f"""\
        Case: {self.casedir}
        Time: {self.time} ({self.time_index + 1} / {len(self.available_times)})
        """
            )
            + f"""{self.multi_block}"""
        )
