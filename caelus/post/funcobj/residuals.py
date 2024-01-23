# -*- coding: utf-8 -*-

"""\
Residuals function object processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides a pythonic interface to process OpenFOAM's residual function objects.
"""


from pathlib import Path

import pandas as pd

from .funcobj import FunctionObject


class Residuals(FunctionObject):
    """
    The class retrieves data from ``residuals.dat`` file generated during the run.

    Example:
      >>> post = PostProcessing()        # Get the post processing instance
      >>> residuals = post['residuals']  # Retrieve the residuals object
      >>> df = residuals()               # Dataframe for the time history
      >>> print(df.columns)              # Manipulate dataframe

    """

    _funcobj_type = "residuals"
    _funcobj_libs = "utilityFunctionObjects"

    _dict_properties = [('fields', None)]

    def __call__(self, time=None):
        """Load the residuals time history.

        Args:
            time (str): Name of the time directory.
        """
        dtime = str(time) if time else self.latest_time
        dpath = Path(self.root) / dtime
        dfile = dpath / "residuals.dat"

        if not dfile.exists():
            raise FileNotFoundError(
                f"Residuals time-history not found: {dfile}"
            )

        cols = self._process_cols(dfile)
        df = pd.read_table(dfile, delimiter=r'\s+', comment="#", names=cols)
        return df

    def _process_cols(self, dfile):
        """Read and process column information"""
        with open(dfile, 'r', encoding='utf-8') as fh:
            # Skip first header line
            fh.readline()
            cname_line = fh.readline()
            cols = cname_line.strip("#").split()
            return cols
