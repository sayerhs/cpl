# -*- coding: utf-8 -*-

"""
``caelus.config`` performs the following tasks:

   - Configure the behavior of the Caelus python library using YAML based
     configuration files.

   - Provide an interface to Caelus CML installations and also aid in automated
     discovery of installed Caelus versions.

.. currentmodule:: caelus.config
.. autosummary::
   :nosignatures:

   ~config.get_config
   ~config.reload_config
   ~config.reset_default_config
   ~cmlenv.cml_get_version
   ~cmlenv.cml_get_latest_version
   ~cmlenv.CMLEnv
"""

# pylint: disable=unused-import
from .config import (get_config, reload_config,
                     reset_default_config, CaelusCfg)

from .cmlenv import (cml_get_version, cml_get_latest_version)
