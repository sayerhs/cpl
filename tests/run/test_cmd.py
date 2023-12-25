# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import os

import pytest

from caelus.config import cmlenv, config
from caelus.run.cmd import CaelusCmd


def has_cml(exe_name="blockMesh"):
    try:
        env = cmlenv.cml_get_version()
        bindir = env.bin_dir
        return os.path.exists(os.path.join(bindir, exe_name))
    except:  # pylint: disable=bare-except
        return False


@pytest.mark.skipif(
    has_cml("blockMesh") is False, reason="Cannot find CML executables"
)
def test_caelus_execute(test_casedir):
    env = cmlenv.cml_get_version()
    casedir = str(test_casedir)
    cml_cmd = CaelusCmd("blockMesh", casedir=casedir, cml_env=env)
    cml_cmd()
    assert os.path.exists(os.path.join(casedir, "blockMesh.log"))


def test_caeluscmd_local(test_casedir):
    casedir = str(test_casedir)
    cmd = CaelusCmd("simpleSolver", casedir=casedir)
    assert not cmd.parallel
    cmd.num_mpi_ranks = 12
    assert cmd.parallel
    assert cmd.num_mpi_ranks == 12
    cmd.mpi_extra_args = " --bind-to core "
    assert cmd.mpi_extra_args == " --bind-to core "
    shell_cmd = cmd.prepare_shell_cmd()
    assert "12" in shell_cmd
    assert "simpleSolver  -parallel" in shell_cmd
    cmd()


def test_caeluscmd_slurm(test_casedir, monkeypatch):
    cfg = config.get_config()
    cfg.caelus.system.job_scheduler = "slurm"

    def mock_config():
        return cfg

    monkeypatch.setattr(config, "get_config", mock_config)
    casedir = str(test_casedir)
    cmd = CaelusCmd("simpleSolver", casedir=casedir)
    assert not cmd.parallel
    cmd.num_mpi_ranks = 12
    assert cmd.parallel
    assert cmd.num_mpi_ranks == 12
    cmd.mpi_extra_args = " --bind-to core "
    assert cmd.mpi_extra_args == " --bind-to core "
    shell_cmd = cmd.prepare_shell_cmd()
    assert "simpleSolver  -parallel" in shell_cmd
    cmd()
