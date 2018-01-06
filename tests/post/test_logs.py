# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import os
from caelus.post.logs import LogProcessor

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
