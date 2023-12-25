# -*- coding: utf-8 -*-

"""\
Wrapper to LMod functionality
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path

from .pyutils import import_script

_lgr = logging.getLogger(__name__)


def _initialize_module_cmd():
    """Helper function to import python module command"""
    if "LMOD_PKG" not in os.environ:
        _lgr.warning("Cannot find LMOD_PKG variable")
        return None

    mod_file = Path(os.environ['LMOD_PKG']) / 'init' / 'env_modules_python.py'
    if not mod_file.exists():
        _lgr.warning("Cannot find LMod python module")
        return None

    return import_script(str(mod_file))


class ModuleWrapper:
    """Wrapper for module environment"""

    def __init__(self):
        self._module_cmd = None

    @property
    def module_cmd(self):
        """Module command used to interact with environment"""
        if not self._module_cmd:
            lmod = _initialize_module_cmd()
            if lmod:
                self._module_cmd = getattr(lmod, "module")

        return self._module_cmd

    def exec_module_cmd(self, cmd, *args):
        """Execute a module command"""
        if not self.module_cmd:
            raise RuntimeError("Cannot find module command")

        lmod = self.module_cmd
        lmod(cmd, *args)

    def load(self, pkg, *args):
        """Load specified modules"""
        self.exec_module_cmd("load", pkg, *args)

    def unload(self, pkg, *args):
        """Unload specified modules"""
        self.exec_module_cmd("unload", pkg, *args)

    def purge(self):
        """Purge all modules"""
        self.exec_module_cmd("purge")

    @contextmanager
    def with_modules(self, *args):
        """Execute a block with modules loaded"""
        try:
            self.load(*args)
            yield
        finally:
            self.unload(*args)


module = ModuleWrapper()
