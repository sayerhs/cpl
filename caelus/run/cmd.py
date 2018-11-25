# -*- coding: utf-8 -*-

"""\
Caelus Job Manager Interface
----------------------------

"""

import os
import logging

from ..config import config
from ..utils import osutils
from .hpc_queue import get_job_scheduler

_lgr = logging.getLogger(__name__)

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

        #: Handle to the subprocess instance running the command
        self.runner = get_job_scheduler()(self.cml_exe)

        #: Is this a parallel run
        self.parallel = False
        self.num_mpi_ranks = 1
        #: Arguments passed to the CML executable
        self.cml_exe_args = ""
        #: Extra arguments passed to MPI
        self.mpi_extra_args = ""

        self.job_id = None

    @property
    def num_mpi_ranks(self):
        """Number of MPI ranks for a parallel run"""
        return self.runner.num_ranks

    @num_mpi_ranks.setter
    def num_mpi_ranks(self, nranks):
        nranks = int(nranks)
        self.runner.num_ranks = nranks
        if nranks > 1:
            self.parallel = True

    @property
    def mpi_extra_args(self):
        """Extra arguments to pass to MPI command"""
        return self.runner.mpi_extra_args

    @mpi_extra_args.setter
    def mpi_extra_args(self, value):
        self.runner.mpi_extra_args = value

    def prepare_exe_cmd(self):
        """Prepare the shell command and return as a string

        Returns:
            The CML command invocation with all its options
        """
        cmd_args = (" -parallel " + self.cml_exe_args
                    if self.parallel else
                    self.cml_exe_args)
        cmd_line = self.cml_exe + " " + cmd_args
        if self.runner.is_job_scheduler():
            cmd_line += " >& %s"%self.output_file
        else:
            self.runner.stdout = self.output_file
        return cmd_line

    def prepare_shell_cmd(self):
        """Prepare the complete command line string as executed"""
        return (self.runner.prepare_mpi_cmd() + " " + self.prepare_exe_cmd()
                if self.parallel else
                self.prepare_exe_cmd())

    def __call__(self, wait=True, job_dependencies=None):
        """Run the executable"""
        with osutils.set_work_dir(self.casedir):
            runner = self.runner
            runner.cml_env = self.cml_env
            runner.script_body = self.prepare_shell_cmd()
            if runner.is_job_scheduler(): # pylint: disable=no-else-return
                self.job_id = runner(
                    job_dependencies=job_dependencies)
                return 0
            else:
                return runner(wait=wait)
