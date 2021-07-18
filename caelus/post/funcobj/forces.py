# -*- coding: utf-8 -*-

"""\
Force and Force coefficients interface
----------------------------------------
"""

import re
from io import StringIO
from pathlib import Path

import pandas as pd

from .funcobj import FunctionObject


class ForceCoeffs(FunctionObject):
    """Force coefficients"""

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
        """Load the data and return a dataframe"""
        dtime = str(time) if time else self.latest_time
        dpath = Path(self.root) / dtime
        fname = dpath / "coefficient.dat"
        if not fname.exists():
            raise FileNotFoundError(
                f"Force coefficients output not found: {fname}")

        with open(fname, 'r') as fh:
            prev = ""
            for line in fh:
                if line[0] != "#":
                    break
                prev = line
            cols = prev.strip("#").split()

        fcoeffs = pd.read_table(
            fname, delimiter=r'\s+', comment="#", names=cols)
        return fcoeffs


class Forces(FunctionObject):
    """Forces interface"""

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
        df = pd.read_table(
            buf, delimiter=r'\s+', comment="#", names=cols)
        return df

    def _col_names(self, prefix):
        """Get column names"""
        types = "x y z px py pz vx vy vz".split()
        return ['Time'] + [prefix + tx for tx in types]

    def __call__(self, time=None):
        """Load the forces/moments file and return a dataframe"""
        dtime = str(time) if time else self.latest_time
        dpath = Path(self.root) / dtime

        forces = self._parse_file(
            dpath / "force.dat",
            self._col_names('F'))
        moments = self._parse_file(
            dpath / "moment.dat",
            self._col_names('M'))
        moments.drop(columns=['Time'])
        return pd.concat([forces, moments])
