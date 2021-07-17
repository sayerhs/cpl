# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import pytest

from caelus.config import get_config, cmlenv
from caelus.io.dictfile import ControlDict

class MockCMLEnv(object):
    """Mock CMLEnv object"""

    @property
    def project_dir(self):
        return "~/Caelus/caelus-7.04"

    @property
    def bin_dir(self):
        return "~/Caelus/caelus-7.04/bin"

    @property
    def mpi_bindir(self):
        return "~/Caelus/caelus-7.04/mpi/bin"

    @property
    def lib_dir(self):
        return "~/Caelus/caelus-7.04/lib"

    @property
    def mpi_libdir(self):
        return "~/Caelus/caelus-7.04/mpi_lib"

    @property
    def user_dir(self):
        return "~/Caelus/user-7.04"

    @property
    def user_bindir(self):
        return "~/Caelus/user-7.04/bin"

    @property
    def user_libdir(self):
        return "~/Caelus/user-7.04/lib"

    @property
    def etc_dirs(self):
        return []

    def etc_file(self, fname):
        return "~/Caelus/caelus-7.04/etc/" + fname

    @property
    def environ(self):
        """Return an empty environment"""
        return {}

def mock_cml_get_latest_version():
    return MockCMLEnv()

@pytest.fixture(autouse=True)
def patch_cml_execution(monkeypatch):
    monkeypatch.setattr(cmlenv, "cml_get_latest_version",
                        mock_cml_get_latest_version)
    monkeypatch.setattr(cmlenv, "cml_get_version",
                        mock_cml_get_latest_version)

def test_dictfile_load(test_casedir):
    cdict = ControlDict.read_if_present(casedir=str(test_casedir))
    assert cdict.application == "pisoSolver"
    assert cdict.writeFormat == "ascii"

def test_dictfile_expand(test_casedir):
    cdict = ControlDict.read_if_present(casedir=str(test_casedir))
    funcs = cdict.functions
    fkeys = funcs.keys()
    assert len(fkeys) == 3

    assert all(ff in fkeys
               for ff in "samples sampleIso samplePlanes".split())

    assert funcs.samples.type == "sets"
    assert funcs.sampleIso.type == "surfaces"
    assert funcs.samplePlanes.type == "surfaces"

    assert len(funcs.samples.sets) == 4
    assert len(funcs.sampleIso.surfaces) == 1
    assert len(funcs.samplePlanes.surfaces) == 1

    planes = funcs.samplePlanes
    assert len(planes.fields) == 4

    offsets = planes.surfaces.planes.offsets
    assert len(offsets) == 9
