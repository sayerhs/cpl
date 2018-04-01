# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import subprocess
import shlex
import pytest
from caelus.utils import osutils
from caelus.config import cmlenv, config
from caelus.run import hpc_queue as hq

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
    def environ(self):
        """Return an empty environment"""
        return {}

def mock_cml_get_latest_version():
    return MockCMLEnv()

def test_get_job_scheduler(monkeypatch):
    types = "no_mpi local_mpi slurm pbs".split()
    cfg = config.get_config()
    def mock_config():
        return cfg
    monkeypatch.setattr(config, "get_config", mock_config)
    for jtype in types:
        cfg.caelus.system.job_scheduler = jtype
        jcls = hq.get_job_scheduler()
        assert(jcls == hq._hpc_queue_map[jtype])

def test_caelus_execute(monkeypatch):
    cml_cmd = "mpiexec -np 4 simpleSolver -parallel"
    monkeypatch.setattr(subprocess, "Popen", MockPopen)
    monkeypatch.setattr(cmlenv, "cml_get_latest_version",
                        mock_cml_get_latest_version)
    task = hq.caelus_execute(cml_cmd)
    cmd_list = shlex.split(cml_cmd)
    assert(task.cml_cmd == cmd_list)

    task = hq.caelus_execute(cmd_list)
    assert(task.cml_cmd == cmd_list)

def test_serial_job(monkeypatch, tmpdir):
    cmd_line = "blockMesh -help"
    cmd_list = shlex.split(cmd_line)
    monkeypatch.setattr(subprocess, "Popen", MockPopen)
    monkeypatch.setattr(cmlenv, "cml_get_latest_version",
                        mock_cml_get_latest_version)
    sjob = hq.SerialJob("blockMesh")

    with pytest.raises(RuntimeError):
        sjob()

    assert(not sjob.is_parallel())
    assert(not sjob.is_job_scheduler())
    assert(sjob.get_queue_settings() == "")
    assert(sjob.prepare_mpi_cmd() == "")

    sjob.script_body = cmd_line
    cdir = tmpdir.mkdir("hpc_serial")
    with osutils.set_work_dir(str(cdir)):
        sjob(wait=False)
        assert (sjob.task.cml_cmd == cmd_list)
        logfile = cdir.join("blockMesh.log")
        assert(logfile.check())

def test_parallel_job(monkeypatch, tmpdir):
    monkeypatch.setattr(subprocess, "Popen", MockPopen)
    monkeypatch.setattr(cmlenv, "cml_get_latest_version",
                        mock_cml_get_latest_version)
    job = hq.ParallelJob("simpleSolver")
    job.num_ranks = 12
    job.mpi_extra_args = " --bind-to core "

    with pytest.raises(RuntimeError):
        job()

    assert(job.is_parallel())
    assert(not job.is_job_scheduler())
    assert(job.get_queue_settings() == "")
    mpi_prefix = job.prepare_mpi_cmd()
    assert("12" in mpi_prefix)
    assert("--bind-to core" in mpi_prefix)

    cmd_line = "mpiexec -np 12 simpleSolver -parallel"
    cmd_list = shlex.split(cmd_line)
    job.script_body = cmd_line
    cdir = tmpdir.mkdir("hpc_parallel")
    with osutils.set_work_dir(str(cdir)):
        job(wait=False)
        assert (job.task.cml_cmd == cmd_list)
        logfile = cdir.join("simpleSolver.log")
        assert(logfile.check())


def test_slurm_job(monkeypatch, tmpdir):
    monkeypatch.setattr(subprocess, "Popen", MockPopen)
    monkeypatch.setattr(cmlenv, "cml_get_latest_version",
                        mock_cml_get_latest_version)
    job = hq.SlurmQueue("simpleSolver")
    job.num_ranks = 12
    job.mpi_extra_args = " --bind-to core "

    with pytest.raises(RuntimeError):
        job()

    assert(job.is_parallel())
    assert(job.is_job_scheduler())
    mpi_prefix = job.prepare_mpi_cmd()
    assert("--bind-to core" in mpi_prefix)

    job.process_run_env()
    run_env = job.env_config
    assert("MPI_BUFFER_SIZE" in run_env)

    qopts = job.get_queue_settings()
    assert("--ntasks 12" in qopts)

    cmd_line = "mpiexec -np 12 simpleSolver -parallel"
    job.script_body = cmd_line
    cdir = tmpdir.mkdir("hpc_slurm")
    jdeps = ["1234", "1235"]
    with osutils.set_work_dir(str(cdir)):
        job_id = job(job_dependencies=jdeps)
        assert(job_id == "1234")
        assert(cdir.join("simpleSolver_slurm.job").check())

    job.delete("1234")
