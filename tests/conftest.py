# -*- coding: utf-8 -*-

import os
import shutil
import pytest

script_dir = os.path.dirname(__file__)

def copy_casedir(tmpldir, dirname):
    """Copy a case directory"""
    for fpath in os.listdir(tmpldir):
        abspath = os.path.join(tmpldir, fpath)
        if os.path.isdir(abspath):
            destdir = os.path.join(
                dirname, os.path.basename(fpath))
            shutil.copytree(abspath, destdir)
        else:
            shutil.copy(abspath, dirname)

@pytest.fixture(scope='session')
def template_casedir(tmpdir_factory):
    """Template read-only case directory for testing purposes"""
    casedir = tmpdir_factory.mktemp("__template_casedir")
    dirname = str(casedir)
    tmpldir = os.path.join(script_dir, "_casedir_template")
    copy_casedir(tmpldir, dirname)
    return casedir

@pytest.fixture
def test_casedir(tmpdir_factory):
    """Create a test directory for manipulation"""
    casedir = tmpdir_factory.mktemp("__test_casedir")
    dirname = str(casedir)
    tmpldir = os.path.join(script_dir, "_casedir_template")
    copy_casedir(tmpldir, dirname)
    return casedir
