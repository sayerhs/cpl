# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import pytest

from caelus.config import cmlenv, get_config
from caelus.io import dtypes
from caelus.io.caelusdict import CaelusDict
from caelus.io.dictfile import ControlDict, TurbulenceProperties
from caelus.utils import osutils


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
    monkeypatch.setattr(
        cmlenv, "cml_get_latest_version", mock_cml_get_latest_version
    )
    monkeypatch.setattr(cmlenv, "cml_get_version", mock_cml_get_latest_version)


def test_dictfile_load(test_casedir):
    cdict = ControlDict.read_if_present(casedir=str(test_casedir))
    assert cdict.application == "pisoSolver"
    assert cdict.writeFormat == "ascii"
    assert "application" in cdict.keys()
    assert cdict['application'] == "pisoSolver"
    assert "controlDict" in repr(cdict)
    assert "application" in str(cdict)


def test_dictfile_create(test_casedir):
    with osutils.set_work_dir(str(test_casedir)):
        cdict = ControlDict()
        assert hasattr(cdict, "header")
        cdict.functions = CaelusDict(a=1)
        with pytest.raises(TypeError):
            cdict.functions = 10

        with pytest.raises(ValueError):
            cdict.writeControl = "onEnd"


def test_turbulence_props(test_casedir):
    with osutils.set_work_dir(str(test_casedir)):
        turb = TurbulenceProperties.read_if_present()
        rans = turb.get_turb_file()
        assert rans.model == "realizableKE"

        turb.simulationType = "LESModel"
        les = turb.get_turb_file()
        assert les.model == "Smagorinsky"
        assert les.delta == "cubeRootVol"


def test_dictfile_expand(test_casedir):
    cdict = ControlDict.read_if_present(casedir=str(test_casedir))
    funcs = cdict.functions
    fkeys = funcs.keys()
    assert len(fkeys) == 3

    assert all(ff in fkeys for ff in "samples sampleIso samplePlanes".split())

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


def test_caelus_dict_expands():
    """Test Caelus dictionary expands"""
    cdict = CaelusDict()
    cdict["entry1"] = CaelusDict(a=1, b=2)
    cdict['entry2'] = CaelusDict(
        macro_0001=dtypes.MacroSubstitution("${entry1}")
    )
    cdict['macro_003'] = dtypes.Directive("#remove", '"entry1"')
    out = cdict._foam_expand_includes()
    out._foam_expand_macros()
    assert out.entry2.a == 1
    assert "entry1" not in out
    out_str = str(out)
    assert "entry2" in out_str
