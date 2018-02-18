# -*- coding: utf-8 -*-

"""\
Caelus Job Manager Interface
----------------------------

"""

import sys
import os
import shlex
import subprocess
import logging

from ..config import config, cmlenv
from ..utils import osutils

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
        env (CMLEnv): An instance representing the CML installation (default: la
test)
        stdout: A file handle where standard output is redirected
        stderr: A file handle where standard error is redirected

    Returns:
        subprocess.Popen : The task instance
    """
    renv = env or cmlenv.cml_get_latest_version()
    cmd_popen = cmd if isinstance(cmd, list) else shlex.split(cmd)
    _lgr.debug("Executing shell command: %s", ' '.join(cmd_popen))
    task = subprocess.Popen(
        cmd_popen, stdout=stdout, stderr=stderr, env=renv.environ)
    return task

class CaelusCmd(object):
    """CML execution interface.

    CaelusCmd is a high-level interface to execute CML binaries within an
    appropriate enviroment across different operating systems.
    """

    def __init__(self, cml_exe,
                 casedir=None,
                 cml_env=None,
                 output_file=None):
        """
        Args:
            cml_exe (str): The binary to be executed (e.g., blockMesh)
            casedir (path): Absolute path to case directory
            cml_env (CMLEnv): Environment used to run the executable
            output_file (file): Filename to redirect all output
        """
        #: CPL configuration object
        self.cfg = config.get_config()
        #: CML program to be executed
        self.cml_exe = cml_exe
        #: Case directory
        self.casedir = casedir or os.getcwd()
        #: CML version used for this run
        self.cml_env = cml_env
        exe_base, _ = os.path.splitext(
            os.path.basename(cml_exe))
        #: Log file where all output and error are captured
        self.output_file = (output_file or
                            "%s.log"%exe_base)

        #: Is this a parallel run
        self.parallel = False
        self.num_mpi_ranks = 1
        #: Arguments passed to the CML executable
        self.cml_exe_args = ""
        #: Extra arguments passed to MPI
        self.mpi_extra_args = ""

        #: Handle to the subprocess instance running the command
        self.task = None

    @property
    def num_mpi_ranks(self):
        """Number of MPI ranks for a parallel run"""
        return self._num_mpi_ranks

    @num_mpi_ranks.setter
    def num_mpi_ranks(self, nranks):
        self._num_mpi_ranks = int(nranks) #pylint: disable=attribute-defined-outside-init
        if nranks > 1:
            self.parallel = True

    def prepare_mpi_cmd(self):
        """Prepare the MPI invocation

        Returns:
            A command line string containing the MPI run command with all its
            required options.
        """
        cmd_tmpl = ("mpiexec -localonly %d "
                    if osutils.ostype() == "windows"
                    else "mpiexec -np %d ")
        mpi_cmd = cmd_tmpl%self.num_mpi_ranks
        return mpi_cmd + self.mpi_extra_args

    def prepare_exe_cmd(self):
        """Prepare the shell command and return as a string

        Returns:
            The CML command invocation with all its options
        """
        cmd_args = (" -parallel " + self.cml_exe_args
                    if self.parallel else
                    self.cml_exe_args)
        return self.cml_exe + " " + cmd_args

    def prepare_shell_cmd(self):
        """Prepare the complete command line string as executed"""
        return (self.prepare_mpi_cmd() + " " + self.prepare_exe_cmd()
                if self.parallel else
                self.prepare_exe_cmd())

    def __call__(self, wait=True):
        """Run the executable

        If ``wait`` is True, then the status of the command will be returned
        upon return, else returns None.
        """
        with osutils.set_work_dir(self.casedir):
            with open(self.output_file, 'w') as fh:
                cmdline = self.prepare_shell_cmd()
                task = caelus_execute(
                    cmdline,
                    env=self.cml_env,
                    stdout=fh,
                    stderr=subprocess.STDOUT)
                self.task = task
                if wait:
                    status = task.wait()
                    if status != 0:
                        _lgr.error("Error running exe %s in %s",
                                   self.cml_exe,
                                   self.casedir)
                    return status
