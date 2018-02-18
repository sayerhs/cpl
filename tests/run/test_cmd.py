# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import os
import pytest
from caelus.config.cmlenv import cml_get_version
from caelus.run.cmd import CaelusCmd

def has_cml(exe_name="blockMesh"):
    try:
        env = cml_get_version()
        bindir = env.bin_dir
        return os.path.exists(
            os.path.join(bindir, exe_name))
    except: # pylint: disable=bare-except
        return False

@pytest.mark.skipif(has_cml("blockMesh") is False,
                    reason="Cannot find CML executables")
def test_caelus_execute(test_casedir):
    env = cml_get_version()
    casedir = str(test_casedir)
    cml_cmd = CaelusCmd(
        "blockMesh",
        casedir=casedir,
        cml_env=env)
    cml_cmd()
    assert(os.path.exists(
        os.path.join(casedir, "blockMesh.log")))
