# -*- coding: utf-8 -*-

"""
Testing function objects
"""

import os

import pytest

from caelus.config import cmlenv, get_config
from caelus.post.funcobj.functions import PostProcessing
from caelus.post.funcobj.sampling import SampledSets, Sampling

script_dir = os.path.dirname(__file__)


class MockCMLEnv(object):
    """Mock CMLEnv object"""

    @property
    def project_dir(self):
        return "~/Caelus/caelus-7.04"

    @property
    def etc_dirs(self):
        return []

    def etc_file(self, fname):
        return "~/Caelus/caelus-7.04/etc/" + fname


def mock_cml_get_latest_version():
    return MockCMLEnv()


@pytest.fixture(autouse=True)
def patch_cml_execution(monkeypatch):
    monkeypatch.setattr(
        cmlenv, "cml_get_latest_version", mock_cml_get_latest_version
    )
    monkeypatch.setattr(cmlenv, "cml_get_version", mock_cml_get_latest_version)


@pytest.mark.filterwarnings("ignore: `np.bool`")
def test_post_processing():
    """Test postprocessing"""
    post = PostProcessing(casedir=os.path.join(script_dir, "_post_template"))
    assert len(post.keys()) == 5
    assert len(list(post.filter('forceCoeffs'))) == 1
    with pytest.raises(ValueError):
        list(post.filter('fieldFunctionObjects'))

    fcoeffs = post['forceCoeffs1']()
    assert fcoeffs.shape == (5, 13)
    for cname in "Cl Cs Cd".split():
        assert cname in fcoeffs.columns

    forces = post['forces1']()
    assert len(forces.columns) == 19
    assert forces.shape == (7, 19)

    residuals = post['residuals']()
    assert len(residuals.columns) == 7
    assert residuals.shape == (8, 7)

    samples = post['samples']
    assert samples.latest_time == "2000"
    line = samples['x_0mCell']
    cols = line().columns
    assert line.num_coord_cols == 1
    assert line().shape == (57, 7)
    assert "U_5" in line._process_field_names(["U"], 6)
    assert "epsilon" in line.fields
    assert "epsilon" in cols
    assert "U_z" in cols
    assert "z" in cols
    assert "x" not in cols

    # Check vtk load
    samples.setFormat = "vtk"
    lvtk = line('1000')
    lvtk1 = line('1000')
    assert id(lvtk) == id(lvtk1)

    surf = post['samplePlanes']['planes']()
    assert len(surf.cell_data) == 4
    surf1 = post['samplePlanes']['planes']()
    assert id(surf) == id(surf1)


def test_funcobj():
    """Test funcob types"""
    sets = SampledSets.create(name="sampling")
    sets.timeStart = 1000
    sets.writeControl = 'onEnd'
    with pytest.raises(ValueError):
        sets.writeControl = 'bananas'

    with pytest.raises(RuntimeError):
        Sampling("sampling", {})
