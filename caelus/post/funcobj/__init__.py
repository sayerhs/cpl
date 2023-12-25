# -*- coding: utf-8 -*-

"""\
OpenFOAM post-processing interface
------------------------------------

The ``funcobj`` package allows user to access the outputs created using
OpenFOAM's ``functionObjects`` utilities. It can be used to load raw and vtk
files into python data structures (e.g., ``pandas.DataFrame``) for further
analysis and plotting. Currently, the package supports sampling (``sets`` and
``surfaces``) as well as forces (``forces`` and ``forceCoeffs``) function
objects.

.. currentmodule: caelus.post.funcobj
.. autosummary::
   :nosignatures:

   ~functions.PostProcessing
   ~forces.ForceCoeffs
   ~forces.Forces
   ~sampling.SampledSets
   ~sampling.SampledSurfaces
"""

from .forces import ForceCoeffs
from .functions import PostProcessing
from .sampling import SampledSets, SampledSurfaces
