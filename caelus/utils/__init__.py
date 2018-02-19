# -*- coding: utf-8 -*-

"""
Collection of low-level utilities that are accessed by other packages within
CPL, and other code snippets that do not fit elsewhere within CPL. The modules
present within utils package must only depend on external libraries or other
modules within util, they must not import modules from other packages within
CPL.

.. currentmodule:: caelus.utils
.. autosummary::
   :nosignatures:

   ~struct.Struct
   osutils
"""

from .struct import Struct
