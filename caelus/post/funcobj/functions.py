# -*- coding: utf-8 -*-

"""\
Post-processing interface
--------------------------

This module contains the implementation of :class:`PostProcessing` the main
entry point for accessing OpenFOAM's ``postProcessing`` outputs.

Example:
  >>> post = PostProcessing() # In case directory
  >>> print("Available objects: ", post.keys())
  Available objects:  ['samples', 'samplePlanes', 'forceCoeffs1']
  >>> fcoeffs = post['forceCoeffs1']
  >>> #print details
  ... print(fcoeffs.magUInf, fcoeffs.liftDir, fcoeffs.dragDir)
  ...
  20 [0 0 1] [1 0 0]
  >>> # Get dataframe corresponding to `coefficient.dat`
  ... df = fcoeffs()
  ... print(df[['Cl', 'Cd']].head())
  ...
           Cl        Cd
  0  0.031805  0.003195
  1  0.078845  0.001883
  2  0.106916  0.001444
  3  0.106786  0.001842
  4  0.079757  0.002850
  >>> df.columns # show available columns
  Index(['Time', 'Cd', 'Cs', 'Cl', 'CmRoll', 'CmPitch', 'CmYaw', 'Cd(f)',
         'Cd(r)', 'Cs(f)', 'Cs(r)', 'Cl(f)', 'Cl(r)'],
        dtype='object')
  >>>
"""

import logging
import os
from pathlib import Path

from ...io import ControlDict
from ...io.caelusdict import CaelusDict
from ...io.dtypes import FoamType
from .forces import ForceCoeffs, Forces, LiftDrag
from .residuals import Residuals
from .sampling import SampledSets, SampledSurfaces
from .volume_report import VolumeReport

_func_objects_list = [
    ForceCoeffs,
    Forces,
    LiftDrag,
    Residuals,
    SampledSets,
    SampledSurfaces,
    VolumeReport,
]

_func_obj_map = {fobj.funcobj_type(): fobj for fobj in _func_objects_list}

_lgr = logging.getLogger(__name__)


class PostProcessing:
    """Main entry point for accessing OpenFOAM ``postProcessing`` data."""

    def __init__(
        self, casedir=None, func_dict=None, raise_on_error: bool = False
    ):
        """
        If the function object dictionary is not provided as an argument, the
        class will attempt to infer the functions activated in ``controlDict``
        file.

        Args:
            casedir (path): Path to the case directory (default: cwd)
            func_dict (CaelusDict): Function objects dictionary
            raise_on_error (bool): Raise exception if some objects fail to process

        """
        #: Absolute path to the case directory
        self.casedir = Path(casedir or os.getcwd())

        if func_dict is not None:
            #: Input dictionary for this function object
            self.data = func_dict
        else:
            cdict = ControlDict.read_if_present(casedir=self.casedir)
            self.data = cdict.functions or CaelusDict()

        fobj = {}
        for k, v in self.data.items():
            if isinstance(v, FoamType):
                continue

            ftype = v['type']
            if ftype not in _func_obj_map:
                _lgr.info("Skipping function object: %s (%s)", k, ftype)
                continue
            if not (self.root / k).exists():
                _lgr.warning(
                    "Missing postProcessing entry for %s (%s)", k, ftype
                )
                continue

            try:
                fcls = _func_obj_map[ftype]
                fobj[k] = fcls(k, v, casedir=self.casedir)
            except Exception:
                _lgr.exception(
                    "Failed to parse function object entry: %s (%s)", k, ftype
                )
                if raise_on_error:
                    raise
        self.func_objects = fobj

    def filter(self, func_type):
        """Retrieve function obects of a particular type.

        The filter method is used to select function objects of a certain
        ``type``. This is useful when the custom user-defined names might not
        correspond to the exact type of object.

        Currently supported: ``sets``, ``surfaces``, ``forces``,
        ``forceCoeffs``.

        Example:
           >>> fig = plt.figure()
           >>> for fcoeff in post.filter('forceCoeffs'):
           ...    df = fcoeff('0')
           ...    plt.plot(df['Time'], df['Cl'])

        Args:
            func_type (str): Type of function object

        Yields:
            FunctionObject: Function object instances

        """
        if func_type not in _func_obj_map:
            raise ValueError(
                f"Invalid function type = '{func_type}'.\nValid types are:"
                "{_func_obj_map.keys()}"
            )
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
        """Get the function object interface corresponding to the key."""
        return self.func_objects[key]
