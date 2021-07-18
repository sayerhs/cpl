# -*- coding: utf-8 -*-

"""\
Post-processing interface
--------------------------
"""

import os
import logging
from pathlib import Path

from ...io import ControlDict
from ...io.caelusdict import CaelusDict
from .sampling import SampledSets, SampledSurfaces
from .forces import ForceCoeffs, Forces

_func_objects_list = [
    ForceCoeffs,
    Forces,
    SampledSets,
    SampledSurfaces,
]

_func_obj_map = {fobj.funcobj_type(): fobj for fobj in _func_objects_list}

_lgr = logging.getLogger(__name__)


class PostProcessing:
    """Interface to access OpenFOAM post-processing data."""

    def __init__(self, casedir=None, func_dict=None):
        """
        Args:
            casedir (path): Path to the case directory
            func_dict (CaelusDict): Function objects dictionary
        """
        self.casedir = Path(casedir or os.getcwd())

        if func_dict is not None:
            self.data = func_dict
        else:
            cdict = ControlDict.read_if_present()
            self.data = cdict.functions or CaelusDict()

        fobj = {}
        for k, v in self.data.items():
            if not (self.root / k).exists():
                _lgr.warning("Missing postProcessing entry for %s", k)
            ftype = v['type']
            fcls = _func_obj_map[ftype]
            fobj[k] = fcls(k, v, casedir=self.casedir)
        self.func_objects = fobj

    def filter(self, func_type):
        """Filter and return objects of a particular type"""
        if func_type not in _func_obj_map:
            raise ValueError(
                f"Invalid function type = '{func_type}'.\nValid types are:"
                "{_func_obj_map.keys()}")
        fcls = _func_obj_map[func_type]
        for val in self.func_objects.values():
            if isinstance(val, fcls):
                yield val

    @property
    def root(self):
        """Return path to the postProcessing directory."""
        return self.casedir / "postProcessing"

    def keys(self):
        """Return the names of the function objects"""
        return list(self.func_objects.keys())

    def __getitem__(self, key):
        """Return function object"""
        return self.func_objects[key]
