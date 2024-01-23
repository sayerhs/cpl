# -*- coding: utf-8 -*-

"""\
Python interface to ``volumeReport`` function object.
"""

import re
from io import StringIO
from pathlib import Path

import pandas as pd

from .funcobj import FunctionObject


class VolumeReport(FunctionObject):
    """Load the volume report time-history data."""

    _funcobj_type = "volumeReport"
    _funcobj_libs = "report"

    _dict_properties = [
        ("logToFile", True),
        ("fields", None),
        ("regions", None),
    ]

    def __call__(self, time=None):
        """Load the volume report file and return a dataframe."""
        dtime = str(time) if time else self.latest_time
        dpath = Path(self.root) / dtime
        fname = dpath / "volumeReport.dat"

        if not fname.exists():
            raise FileNotFoundError(f"Volume report history not found: {fname}")

        with open(fname, 'r', encoding='utf-8') as fh:
            header = fh.readline()
            cols = self._process_columns(header)

            # Parse lines and remove parentheses
            buf = StringIO()
            rexp = re.compile(r'[\(\)]')
            for line in fh:
                buf.write(rexp.sub('', line))
            buf.seek(0)

            # Load as a dataframe
            df = pd.read_table(buf, delimiter=r'\s+', comment="#", names=cols)
            return df

    def _process_columns(self, header: str):
        """Process column names from the header line"""

        def helper(colnames):
            """Helper function to process column names"""
            prev_seen = ""
            for col in colnames:
                if col == "at_location":
                    yield f"{prev_seen}_x"
                    yield f"{prev_seen}_y"
                    yield f"{prev_seen}_z"
                else:
                    prev_seen = col
                    yield col

        rexp = re.compile(r'at location')
        hdr1 = rexp.sub('at_location', header)
        cnames1 = hdr1.strip("#").split()

        return list(helper(cnames1))
