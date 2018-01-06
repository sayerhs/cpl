# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import os.path as pth
from caelus.utils import osutils

def test_ensure_directory(tmpdir):
    """Test ensure_directory"""
    casedir = tmpdir.mkdir("test_case")
    cname = str(casedir)
    newdir = osutils.ensure_directory(pth.join(cname, "test_dir"))
    assert pth.exists(newdir)
