# -*- coding: utf-8 -*-

"""\
Python script import utilities
------------------------------
"""

import sys
import os
import importlib

from . import osutils

def import_script(fname):
    """Dynamically import a script and return the module"""
    fpath = osutils.abspath(fname)

    if not os.path.exists(fpath):
        raise FileNotFoundError("Cannot find file: %s"%fname)

    (moddir, modname, _) = osutils.split_path(fpath)
    try:
        sys.path.append(moddir)
        mspec = importlib.util.spec_from_file_location(modname, fpath)
        module = importlib.util.module_from_spec(mspec)
        mspec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop()
