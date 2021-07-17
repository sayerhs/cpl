# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import os
import tempfile
import shutil
import textwrap
import pytest

from caelus.config import cmlenv, config

dummy_config = """
caelus:
  logging:
    log_to_file: False
    log_file: null

  # Configuration for Caelus CML
  caelus_cml:
    # Pick the latest version of CML available
    default: latest

    # Available versions must be provided in configuration files
    versions:
      - version: "10.11"

      - version: "v2012"
"""

def mock_get_config():
    cfg = config.CaelusCfg.from_yaml(dummy_config)

    def _cfg():
        return cfg
    return _cfg

def teardown_module(module):
    cmlenv.cml_reset_versions()

@pytest.fixture(scope="module")
def caelus_directory():
    """Temporary Caelus root directory for testing"""
    ostype = "windows" if os.name == 'nt' else os.uname()[0].lower()
    root_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(
        root_dir, "Caelus", "caelus-10.11",
        "platforms", "%s64g++DPOpt"%ostype))
    os.makedirs(os.path.join(
        root_dir, "Caelus", "caelus-7.04",
        "platforms", "%s64g++DPOpt"%ostype))
    os.makedirs(os.path.join(
        root_dir, "Caelus", "caelus-6.10",
        "platforms", "%s64g++DPOpt"%ostype))
    for ver in ["10.11", "7.04", "6.10"]:
        fname = os.path.join(
            root_dir, "Caelus", "caelus-%s"%ver, "SConstruct")
        open(fname, 'w').write("#/usr/bin/env python\n")
    yield os.path.join(root_dir, "Caelus")
    shutil.rmtree(root_dir)

@pytest.fixture(scope="module")
def openfoam_directory(tmpdir_factory):
    """Temporary OpenFOAM root directory for testing"""
    temp_dir = tmpdir_factory.mktemp("__test_openfoamdir")
    foam_root = temp_dir / "OpenFOAM"
    foam_root.mkdir()
    foam_2012 = foam_root / "OpenFOAM-v2012"
    foam_2012.mkdir()
    wmake_dir = foam_2012 / "wmake"
    wmake_dir.mkdir()
    meta_info = foam_2012 / "META-INFO"
    meta_info.mkdir()
    api_info = meta_info / "api-info"
    api_info.write_text("""api=2012\npatch=210414\n""", 'utf-8')
    etc_dir = foam_2012 / "etc"
    etc_dir.mkdir()
    bashrc = etc_dir / "bashrc"
    bashrc.write_text(textwrap.dedent("""
    export WM_PROJECT_VERSION=v2012
    export WM_COMPILER_TYPE=system
    export WM_COMPILER=Gcc
    export WM_PRECISION_OPTION=DP
    export WM_LABEL_SIZE=32
    export WM_COMPILE_OPTION=Opt
    export WM_MPLIB=SYSTEMOPENMPI
    export WM_PROJECT=OpenFOAM
    """), 'utf-8')
    yield foam_root

@pytest.fixture(autouse=True)
def no_get_config(monkeypatch, caelus_directory, openfoam_directory):
    """Mock CaelusCfg object for testing"""
    monkeypatch.setattr(config, "get_config", mock_get_config())
    cfg = config.get_config()
    cfg.caelus.caelus_cml.versions[0].path = os.path.join(
        caelus_directory, "caelus-10.11")
    cfg.caelus.caelus_cml.versions[1].path = (
        openfoam_directory / "OpenFOAM-v2012")

@pytest.fixture()
def foam_latest_version_fix():
    """Tweak configuration to provide only OpenFOAM versions"""
    cfg = config.get_config()
    vers = cfg.caelus.caelus_cml.versions
    vers[0] = vers[1]

def test_get_latest_version():
    # ALERT: This is testing the configuration object, not the temporary
    # directory created for other tests.
    cmlenv.cml_reset_versions()
    cver = cmlenv.cml_get_latest_version()
    assert cver.version == "10.11"

def test_get_version():
    # ALERT: This is testing the configuration object, not the temporary
    # directory created for other tests.
    cmlenv.cml_reset_versions()
    cmlenv.cml_get_version("10.11")
    with pytest.raises(KeyError):
        cmlenv.cml_get_version("3.84")

def test_discover_versions(caelus_directory):
    cvers = cmlenv.discover_versions(caelus_directory)
    assert len(cvers) == 3
    for cobj in cvers:
        assert hasattr(cobj, "version")
        assert cobj.version in ["10.11", "7.04", "6.10"]
        assert cobj.path == os.path.join(caelus_directory,
                                         "caelus-%s"%cobj.version)

def test_determine_platform_dir(caelus_directory):
    ostype = "windows" if os.name == 'nt' else os.uname()[0].lower()
    root_path = os.path.join(caelus_directory, "caelus-10.11")
    bdir_path = cmlenv._determine_platform_dir(root_path)
    bpath_expected = os.path.join(
        root_path, "platforms", "%s64g++DPOpt"%ostype)
    assert bdir_path == bpath_expected

def test_foam_get_latest_version(foam_latest_version_fix):
    # ALERT: This is testing the configuration object, not the temporary
    # directory created for other tests.
    cmlenv.cml_reset_versions()
    cver = cmlenv.cml_get_latest_version()
    assert cver.version == "v2012"

def test_foam_get_version(openfoam_directory):
    cmlenv.cml_reset_versions()
    cenv = cmlenv.cml_get_version("v2012")
    assert cenv.project_dir == (openfoam_directory / "OpenFOAM-v2012")
    assert cenv.version == "v2012"
    assert cenv.foam_api_info.api == "2012"
