# -*- coding: utf-8 -*-

"""\
CML Execution Utilities
-----------------------
"""

import sys
import os
import subprocess
import logging
import shlex
from ..utils import osutils
from ..config.cmlenv import cml_get_latest_version

_lgr = logging.getLogger(__name__)

def caelus_execute(cmd, env=None, stdout=sys.stdout, stderr=sys.stderr):
    """Execute a CML command with the right environment setup

    A wrapper around subprocess.Popen to set up the correct environment before
    invoing the CML executable.

    The command can either be a string or a list of arguments as appropriate
    for Caelus executables.

    Examples:
      caelus_execute("blockMesh -help")

    Args:
        cmd (str or list): The command to be executed
        env (CMLEnv): An instance representing the CML installation (default: latest)
        stdout: A file handle where standard output is redirected
        stderr: A file handle where standard error is redirected

    Returns:
        subprocess.Popen : The task instance
    """
    renv = env or cml_get_latest_version()
    cmd_popen = cmd if isinstance(cmd, list) else shlex.split(cmd)
    task = subprocess.Popen(
        cmd_popen, stdout=stdout, stderr=stderr, env=renv.environ)
    return task

def run_cml_exe(cml_exe, casedir=None, env=None,
               logfile=None, wait=True):
    """Run a CML executable in the given case directory.

    Args:
        casedir (path): Path to the case directory
        cml_exe (str): Name of the executable (e.g., blockMesh, decomposePar, pisoSolver)
        env (CMLEnv): Environment for the Caelus version to use
        logfile (str): Filename for logging outputs (default: ``<cml_exe>.log``)
        wait (bool): If true, wait for the job to complete

    Returns:
        If wait is True, then it returns the status code for the completed job.
        else it returns an instance of subprocess.Popen instance that the user
        can act upon.
    """
    cdir = casedir or os.getcwd()
    with osutils.set_work_dir(cdir):
        logf = logfile or "%s.log"%cml_exe
        with open(logf, 'w') as fh:
            task = caelus_execute(
                cml_exe, env, stdout=fh, stderr=subprocess.STDOUT)
            if wait:
                status = task.wait()
                if status != 0:
                    _lgr.error("Error running executable %s in %s",
                               cml_exe, casedir)
                return status
            else:
                return task


def is_caelus_casedir(root=None):
    """Check if the path provided looks like a case directory.

    A directory is determined to be an OpenFOAM/Caelus case directory if the
    ``system``, ``constant``, and ``system/controlDict`` exist. No check is
    performed to determine whether the case directory will actually run or if a
    mesh is present.
    """
    cdir = os.getcwd() if root is None else root
    return all(os.path.exists(os.path.join(cdir, d))
               for d in ["constant", "system",
                         os.path.join("system", "controlDict")])

def find_case_dirs(basedir):
    """Recursively search for case directories existing in a path.

    Args:
        basedir (path): Top-level directory to traverse
    """
    absdir = osutils.abspath(basedir)
    # is the root directory itself a case directory?
    if is_caelus_casedir(absdir):
        yield absdir
    else:
        for root, dirs, _ in os.walk(absdir):
            for d in list(dirs):
                cdir = os.path.join(root, d)
                if is_caelus_casedir(cdir):
                    dirs.remove(d)
                    yield os.path.relpath(cdir, absdir)
