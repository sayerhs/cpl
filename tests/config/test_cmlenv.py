# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import json
import os
import shutil
import tempfile
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


def add_cml_json(root_dir, ostype, ver="7.04"):
    """Add the json env file"""
    build_opt = "%s64g++DPOpt" % ostype
    etc_dir = os.path.join(root_dir, "Caelus", "caelus-%s" % ver, "etc")
    cml_dict = dict(
        MPI_LIB_PATH="/opt/openmpi/lib",
        CAELUS_USER_DIR="/home/Caelus/user-%s/" % ver,
        CAELUS_USER_APPBIN="/home/Caelus/user-%s/platforms/%s"
        % (ver, build_opt),
    )
    jdict = {build_opt: cml_dict}
    with open(os.path.join(etc_dir, "cml_env.json"), 'w') as fh:
        json.dump(jdict, fh)


@pytest.fixture(scope="module")
def caelus_directory():
    """Temporary Caelus root directory for testing"""
    ostype = "windows" if os.name == 'nt' else os.uname()[0].lower()
    root_dir = tempfile.mkdtemp()
    os.makedirs(
        os.path.join(
            root_dir,
            "Caelus",
            "caelus-10.11",
            "platforms",
            "%s64g++DPOpt" % ostype,
        )
    )
    os.makedirs(
        os.path.join(
            root_dir,
            "Caelus",
            "caelus-7.04",
            "platforms",
            "%s64g++DPOpt" % ostype,
        )
    )
    os.makedirs(
        os.path.join(
            root_dir,
            "Caelus",
            "caelus-6.10",
            "platforms",
            "%s64g++DPOpt" % ostype,
        )
    )
    for ver in ["10.11", "7.04", "6.10"]:
        etc_dir = os.path.join(root_dir, "Caelus", "caelus-%s" % ver, "etc")
        os.makedirs(etc_dir)
        fname = os.path.join(
            root_dir, "Caelus", "caelus-%s" % ver, "SConstruct"
        )
        open(fname, 'w').write("#/usr/bin/env python\n")
    add_cml_json(root_dir, ostype, "7.04")
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
    (foam_2012 / "platforms").mkdir()
    bindir = foam_2012 / "platforms" / "linux64g++DPInt32Opt"
    bindir.mkdir()
    bashrc = etc_dir / "bashrc"
    bashrc.write_text(
        textwrap.dedent(
            f"""
    export WM_PROJECT_VERSION=v2012
    export WM_COMPILER_TYPE=system
    export WM_COMPILER=Gcc
    export WM_PRECISION_OPTION=DP
    export WM_LABEL_SIZE=32
    export WM_COMPILE_OPTION=Opt
    export WM_MPLIB=SYSTEMOPENMPI
    export WM_PROJECT=OpenFOAM
    export FOAM_APPBIN={bindir}
    export FOAM_LIBBIN={bindir}
    export WM_OPTIONS=linux64g++DPInt32Opt
    """
        ),
        'utf-8',
    )
    yield foam_root


@pytest.fixture(autouse=True)
def no_get_config(monkeypatch, caelus_directory, openfoam_directory):
    """Mock CaelusCfg object for testing"""
    monkeypatch.setattr(config, "get_config", mock_get_config())
    cfg = config.get_config()
    cfg.caelus.caelus_cml.versions[0].path = os.path.join(
        caelus_directory, "caelus-10.11"
    )
    cfg.caelus.caelus_cml.versions[1].path = (
        openfoam_directory / "OpenFOAM-v2012"
    )


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
        assert cobj.path == os.path.join(
            caelus_directory, "caelus-%s" % cobj.version
        )


def test_determine_platform_dir(caelus_directory):
    ostype = "windows" if os.name == 'nt' else os.uname()[0].lower()
    root_path = os.path.join(caelus_directory, "caelus-10.11")
    bdir_path = cmlenv._determine_platform_dir(root_path)
    bpath_expected = os.path.join(
        root_path, "platforms", "%s64g++DPOpt" % ostype
    )
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


def test_cmlenv_object(caelus_directory):
    """Test CMLenv properties"""
    proj_dir = os.path.join(caelus_directory, "caelus-10.11")

    def get_new_cfg(ver="10.11"):
        cdir = os.path.join(caelus_directory, "caelus-%s" % ver)
        cfg = config.get_config()
        vers = cfg.caelus.caelus_cml.versions
        vers[0].version = ver
        vers[0].path = cdir
        return vers[0]

    ostype = "windows" if os.name == 'nt' else os.uname()[0].lower()
    cfg1 = get_new_cfg()
    cfg1.user_dir = os.path.join(caelus_directory, "user-10.11")
    cenv = cmlenv.CMLEnv(cfg1)

    assert cenv.root == caelus_directory
    bdir = os.path.join(proj_dir, "platforms", "%s64g++DPOpt" % ostype)
    assert cenv.build_dir == bdir
    assert cenv.lib_dir == os.path.join(bdir, "lib")
    etc_dirs = cenv.etc_dirs
    assert len(etc_dirs) == 1
    assert etc_dirs[0] == os.path.join(proj_dir, "etc")
    assert not cenv.mpi_dir
    assert cenv.environ['CAELUS_PROJECT_DIR'] == proj_dir
    assert "user-10.11" in cenv.user_bindir
    assert "user-10.11" in cenv.user_libdir
    assert "10.11" in repr(cenv)
    assert "10.11" in str(cenv)

    cfg2 = get_new_cfg()
    cfg2.mpi_root = os.path.join(proj_dir, "external", "openmpi")
    cenv = cmlenv.CMLEnv(cfg2)
    assert cenv.mpi_bindir == os.path.join(cfg2.mpi_root, "bin")
    assert cenv.mpi_libdir == os.path.join(cfg2.mpi_root, "lib")

    cfg3 = get_new_cfg()
    cfg3.build_option = "%s64Clang++DPOpt" % ostype
    cenv = cmlenv.CMLEnv(cfg3)
    assert "10.11" in cenv.user_dir
    with pytest.raises(IOError):
        _ = cenv.build_dir

    cfg4 = get_new_cfg("7.04")
    cfg4.build_option = "%s64g++DPOpt" % ostype
    cenv = cmlenv.CMLEnv(cfg4)
    json_file = cenv.etc_file("cml_env.json")


def test_foamenv_object(openfoam_directory):
    proj_dir = os.path.join(openfoam_directory, "OpenFOAM-v2012")

    def get_new_cfg(ver="v2012"):
        cdir = os.path.join(openfoam_directory, "OpenFOAM-%s" % ver)
        cfg = config.get_config()
        vers = cfg.caelus.caelus_cml.versions
        vers[0].version = ver
        vers[0].path = cdir
        return vers[0]

    ostype = "windows" if os.name == 'nt' else os.uname()[0].lower()
    cfg1 = get_new_cfg()
    cfg1.mpi_root = os.path.join(proj_dir, "openmpi")
    os.makedirs(cfg1.mpi_root)
    cenv = cmlenv.FOAMEnv(cfg1)
    assert cenv.root == openfoam_directory
    assert cenv.version == "v2012"
    assert cenv.foam_version == "v2012"
    assert len(cenv.etc_dirs) == 5
    assert "openmpi" in cenv.mpi_libdir
    assert "openmpi" in cenv.mpi_bindir
    if ostype != "windows":
        assert "PATH" in cenv.environ
        bashrc = cenv.etc_file("bashrc")
        assert bashrc is not None
