# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import os
import pytest
from caelus.post.logs import LogProcessor, SolverLog

script_dir = os.path.dirname(__file__)

def test_log_processor(tmpdir):
    casedir = tmpdir.mkdir("test_case")
    cname = str(casedir)
    logfile = casedir.join("solverLog.log")
    logfile.write(open(os.path.join(
        script_dir, "solverLog.log"), 'r').read())
    log = LogProcessor("solverLog.log", cname)
    # Check that the logs directory is created if it doesn't exist
    assert os.path.exists(os.path.join(cname, "logs"))
    log()
    logpath = os.path.join(cname, "logs")
    # Check that all the files are created as expected
    for fname in "Ux Uy p k epsilon clock_time continuity_errors".split():
        fpath = os.path.join(logpath, fname+".dat")
        assert os.path.exists(fpath)

    slog = SolverLog(case_dir=cname)
    assert(len(slog.fields) == 5)

def test_solverlog(tmpdir):
    casedir = tmpdir.mkdir("test_solverlog")
    cname = str(casedir)
    logfile = casedir.join("solverLog.log")
    logfile.write(open(os.path.join(
        script_dir, "solverLog.log"), 'r').read())
    slog = SolverLog(case_dir=cname, logfile=logfile)
    assert(len(slog.fields) == 5)
    vel = slog.residual("Ux")
    assert(len(vel.shape) == 2)
    cerrs = slog.continuity_errors()
    assert(len(cerrs.shape) == 2)
    with pytest.raises(KeyError):
        slog.residual("nonExistent")
    with pytest.raises(KeyError):
        slog.bounding_var("epsilon")

def test_solverlog1(tmpdir):
    with pytest.raises(RuntimeError):
        SolverLog(case_dir=str(tmpdir))
