# -*- coding: utf-8 -*-

"""\
Force and Force coefficients interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides pythonic interface to OpenFOAM's `Forces <https://www.openfoam.com/documentation/guides/latest/doc/guide-function-objects-forces.html>`_
function objects.

"""

import re
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

from .funcobj import FunctionObject


class ForceCoeffs(FunctionObject):
    """
    The class retrieves data from ``coefficient.dat`` file generated during a
    run.

    Example:
      >>> post = PostProcessing()         # Get the post processing instance
      >>> fcoeffs = post['forceCoeffs1']  # Retrieve force coefficients object
      >>> df = fcoeffs()                  # Dataframe for latest time instance
      >>> print(df.columns)               # Examine columns

    """

    _funcobj_type = "forceCoeffs"
    _funcobj_libs = ["forces"]

    _dict_properties = [
        ('patches', None),
        ('liftDir', None),
        ('dragDir', None),
        ('pitchAxis', None),
        ('magUInf', None),
        ('lRef', None),
        ('Aref', None),
    ]

    def __call__(self, time=None):
        """Load the force coefficients file and return as dataframe.

        If ``time`` is provided, the force coefficients are retrieved from the
        corresponding time directory. Otherwise, the data from the latest
        timestep is retrieved.

        Args:
            time (str): Name of the time directory.

        Returns:
            pd.DataFrame: DataFrame corresponding to ``coefficient.dat``

        Raises:
            FileNotFoundError
        """
        dtime = str(time) if time else self.latest_time
        dpath = Path(self.root) / dtime
        fname = dpath / "coefficient.dat"
        if not fname.exists():
            raise FileNotFoundError(
                f"Force coefficients output not found: {fname}"
            )

        with open(fname, 'r') as fh:
            prev = ""
            for line in fh:
                if line[0] != "#":
                    break
                prev = line
            cols = prev.strip("#").split()

        fcoeffs = pd.read_table(
            fname, delimiter=r'\s+', comment="#", names=cols
        )
        return fcoeffs


class Forces(FunctionObject):
    """
    The class retrives data from ``force.dat`` and ``moment.dat`` files
    generated during a run and returns a single Pandas DataFrame containing the
    following columns.

    =======  =====================================
    Column   Value
    =======  =====================================
    Fx       Total force (x-direction)
    Fy       Total force (y-direction)
    Fz       Total force (z-direction)
    Fpx      Pressure force (x-direction)
    Fpy      Pressure force (y-direction)
    Fpz      Pressure force (z-direction)
    Fvx      Viscous force (x-direction)
    Fvy      Viscous force (y-direction)
    Fvz      Viscous force (z-direction)
    Mx       Total moment (x-direction)
    My       Total moment (y-direction)
    Mz       Total moment (z-direction)
    Mpx      Pressure moment (x-direction)
    Mpy      Pressure moment (y-direction)
    Mpz      Pressure moment (z-direction)
    Mvx      Viscous moment (x-direction)
    Mvy      Viscous moment (y-direction)
    Mvz      Viscous moment (z-direction)
    =======  =====================================

    Example:
      >>> post = PostProcessing()   # Get the post processing instance
      >>> forces = post['forces1']  # Retrieve force coefficients object
      >>> df = forces()             # Dataframe for latest time instance
      >>> print(df.columns)         # Examine columns
    """

    _funcobj_type = "forces"
    _funcobj_libs = ["forces"]

    def _parse_file(self, fname, cols):
        """Parse the file and return a dataframe"""
        rexp = re.compile(r'[\(\)]')
        buf = StringIO()

        # Remove parenthesis from rows
        with open(fname, 'r') as fh:
            for line in fh:
                buf.write(rexp.sub('', line))
        buf.seek(0)

        # Load as a dataframe
        df = pd.read_table(buf, delimiter=r'\s+', comment="#", names=cols)
        return df

    def _col_names(self, prefix):
        """Get column names"""
        types = "x y z px py pz vx vy vz".split()
        return ['Time'] + [prefix + tx for tx in types]

    def __call__(self, time=None):
        """Load the forces/moments file and return a dataframe.

        If ``time`` is provided, the force coefficients are retrieved from the
        corresponding time directory. Otherwise, the data from the latest
        timestep is retrieved.

        Args:
            time (str): Name of the time directory.

        Returns:
            pd.DataFrame: DataFrame corresponding to ``force.dat``
            and ``moment.dat``

        Raises:
            FileNotFoundError
        """
        dtime = str(time) if time else self.latest_time
        dpath = Path(self.root) / dtime

        forces = self._parse_file(dpath / "force.dat", self._col_names('F'))
        moments = self._parse_file(dpath / "moment.dat", self._col_names('M'))
        moments.drop(columns=['Time'], inplace=True)
        return pd.concat([forces, moments], axis=1)


class LiftDrag(FunctionObject):
    """A variation of ForceCoeffs that calculates lift/drag for specific use case."""

    _funcobj_type = "liftDrag"
    _funcobj_libs = "forces"

    _dict_properties = [
        ('patches', None),
        ('liftDirection', None),
        ('dragDirection', None),
        ('pitchAxis', None),
        ('Uinf', None),
        ('rhoInfo', None),
        ('referenceArea', None),
        ('referenceLength', None),
        ('nAveragingSteps', 1),
        ('maxCp', 1.0e14),
        ('minCp', 1.0e14),
        ('wheelbase', None),
        ('runOnLastIterOnly', False),
        ('porosity', True),
        ('outputRegionData', False),
        ('writeFields', False),
    ]

    def __call__(self, time: str = None):
        """Load the liftDrag file and return as pandas DataFrame."""
        dtime = str(time) if time else self.latest_time
        dpath = self.root / dtime
        fname = dpath / "liftDrag.dat"

        if not fname.exists():
            raise FileNotFoundError(f"Lift-drag output not found: {fname}")

        data = np.loadtxt(fname)
        return pd.DataFrame(data, columns=self._col_names())

    def _col_names(self):
        """Get the column names for the dataset"""
        return [
            "time",
            "total_lift",
            "front_lift",
            "rear_lift",
            "drag",
            "side_force",
            "x_moment",
            "y_moment",
            "z_moment",
        ]
