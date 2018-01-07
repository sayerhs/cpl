# -*- coding: utf-8 -*-

"""\
CML Execution Utilities
-----------------------
"""

import sys
import subprocess
import shlex
from ..config.cmlenv import cml_get_latest_version

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
