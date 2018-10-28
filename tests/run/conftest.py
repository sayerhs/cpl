# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import subprocess
import pytest

from caelus.config import cmlenv

class MockPopen(object):
    """Mock a Popen instance"""

    def __init__(self, cml_cmd, *args, **kwargs):
        self.cml_cmd = cml_cmd
        self.args = args
        self.kwargs = kwargs

    def communicate(self):
        if "sbatch" in self.cml_cmd:
            return ("Submitted batch job 1234".encode('utf-8'), "")
        elif "qsub" in self.cml_cmd:
            return ("1234".encode('utf-8'), "")
        return ("output", "error")

    def wait(self):
        return 0

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
    def environ(self):
        """Return an empty environment"""
        return {}

def mock_cml_get_latest_version():
    return MockCMLEnv()

@pytest.fixture(autouse=True)
def patch_cml_execution(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", MockPopen)
    monkeypatch.setattr(cmlenv, "cml_get_latest_version",
                        mock_cml_get_latest_version)
    monkeypatch.setattr(cmlenv, "cml_get_version",
                        mock_cml_get_latest_version)
