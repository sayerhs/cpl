# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import os
import tempfile
import shutil
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
    yield os.path.join(root_dir, "Caelus")
    shutil.rmtree(root_dir)

@pytest.fixture(autouse=True)
def no_get_config(monkeypatch, caelus_directory):
    """Mock CaelusCfg object for testing"""
    monkeypatch.setattr(config, "get_config", mock_get_config())
    cfg = config.get_config()
    cfg.caelus.caelus_cml.versions[0].path = os.path.join(
        caelus_directory, "caelus-10.11")

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
