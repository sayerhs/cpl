# -*- coding: utf-8 -*-

"""\
Caelus command
--------------
"""

import os
import logging
from ..utils import osutils
from ..config.cmlenv import cml_get_version
from .core import CaelusSubCmdScript
from ..run.tasks import Tasks
from ..run.core import clone_case, get_mpi_size, run_cml_exe, clean_casedir
from ..post.logs import LogProcessor

_lgr = logging.getLogger(__name__)

class CaelusCmd(CaelusSubCmdScript):
    """Top-level Caelus interface"""

    description = "Caelus Python Utility Interface"

    def cli_options(self):
        """Setup sub-commands for the Caelus application"""
        super(CaelusCmd, self).cli_options()
        subparsers = self.subparsers
        clone = subparsers.add_parser(
            "clone",
            description="Clone a case directory into a new folder.",
            help="Clone case directory")
        tasks = subparsers.add_parser(
            "tasks",
            description="Run pre-defined tasks within a case directory "
            "read from a YAML-formatted file.",
            help="Run tasks from file")
        run = subparsers.add_parser(
            "run",
            description="Run a Caelus executable in the correct environment",
            help="run a Caelus executable in the correct environment")
        logs = subparsers.add_parser(
            "logs",
            description="Process logfiles for a Caelus run",
            help="Process the solver logs for a Caelus run")
        clean = subparsers.add_parser(
            "clean",
            description="Clean a case directory",
            help="clean case directory")

        # Clone action
        clone.add_argument(
            "-m", "--skip-mesh", action='store_true',
            help="skip mesh directory while cloning")
        clone.add_argument(
            "-z", "--skip-zero", action='store_true',
            help="skip 0 directory while cloning")
        clone.add_argument(
            "-s", "--skip-scripts", action='store_true',
            help="skip scripts while cloning")
        clone.add_argument(
            "-e", "--extra-patterns", action='append',
            help="shell wildcard patterns matching additional files to ignore")
        clone.add_argument(
            '-d', '--base-dir', default=os.getcwd(),
            help="directory where the new case directory is created")
        clone.add_argument("template_dir",
                           help="Valid Caelus case directory to clone.")
        clone.add_argument("case_name",
                           help="Name of the new case directory.")
        clone.set_defaults(func=self.clone_case)

        # Tasks action
        tasks.add_argument(
            '-f', '--file', default="caelus_tasks.yaml",
            help="File containing tasks to execute (caelus_tasks.yaml)")
        tasks.set_defaults(func=self.run_tasks)

        # Run action
        run.add_argument(
            '-p', '--parallel', action='store_true',
            help="Run in parallel")
        run.add_argument(
            '-l', '--log-file', default=None,
            help="Filename to redirect command output")
        run.add_argument(
            '-d', '--case-dir', default=os.getcwd(),
            help="path to the case directory")
        run.add_argument(
            'cmd_name',
            help="Name of the Caelus executable")
        run.add_argument(
            'cmd_args', nargs='*',
            help="Additional arguments passed to command")
        run.set_defaults(func=self.run_cmd)

        # Logs action
        logs.add_argument(
            '-l', '--logs-dir', default="logs",
            help="Directory where logs are output (default: logs)")
        logs.add_argument(
            '-d', '--case-dir', default=os.getcwd(),
            help="path to the case directory")
        logs.add_argument(
            "log_file",
            help="Log file (e.g., simpleSolver.log)")
        logs.set_defaults(func=self.process_logs)

        # Clean action
        clean.add_argument(
            '-d', '--case-dir', default=os.getcwd(),
            help="path to the case directory")
        clean.add_argument(
            '-m', '--clean-mesh', action='store_true',
            help="Remove polyMesh directory")
        clean.add_argument(
            '-z', '--clean-zero', action='store_true',
            help="Remove 0 directory")
        clean.add_argument(
            '-p', '--preserve', action='append',
            help="Shell wildcard patterns of extra files to preserve")
        clean.set_defaults(func=self.clean_case)

    def run_tasks(self):
        """Run tasks"""
        args = self.args
        cenv = cml_get_version()
        _lgr.info("Caelus CML version: %s", cenv.version)
        task_file = osutils.abspath(args.file)
        tasks = Tasks.load(task_file)
        tasks(env=cenv)

    def run_cmd(self):
        """Run a Caelus executable"""
        # TODO: Remove duplication between this function and
        # Tasks.cmd_run_command method.
        args = self.args
        cenv = cml_get_version()
        parallel = args.parallel
        cml_exe = args.cmd_name
        exe_args = ' '.join(args.cmd_args)
        exe_base, _ = os.path.splitext(os.path.basename(cml_exe))
        log_file = args.log_file or exe_base + ".log"
        mpi_args = " "
        num_ranks = 0
        if parallel:
            num_ranks = get_mpi_size(args.case_dir)
            mpi_args = " -np %d "%num_ranks
            exe_args = " -parallel " + exe_args
        if parallel:
            _lgr.info("Executing %s in parallel on %d ranks",
                      cml_exe, num_ranks)
        else:
            _lgr.info("Executing %s in serial mode", cml_exe)
        with osutils.set_work_dir(args.case_dir):
            status = run_cml_exe(
                cml_exe, env=cenv, logfile=log_file,
                cml_exe_args=exe_args, mpi_args=mpi_args)
            if status != 0:
                _lgr.error("Error executing command; see %s for details",
                           log_file)
                self.parser.exit(status)

    def clone_case(self):
        """Clone a case directory"""
        args = self.args
        copy_mesh = (not args.skip_mesh)
        copy_zero = (not args.skip_zero)
        copy_scripts = (not args.skip_scripts)
        extra_pat = args.extra_patterns
        template_dir = osutils.abspath(args.template_dir)
        if not (os.path.exists(template_dir) and
                os.path.isdir(template_dir)):
            _lgr.fatal("Cannot find template directory: %s", template_dir)
            self.parser.exit(1)
        if not (os.path.exists(args.base_dir) and
                os.path.isdir(args.base_dir)):
            _lgr.fatal("Base directory does not exist: %s", args.base_dir)
            self.parser.exit(1)
        with osutils.set_work_dir(args.base_dir):
            clone_case(args.case_name,
                       template_dir,
                       copy_polymesh=copy_mesh,
                       copy_zero=copy_zero,
                       copy_scripts=copy_scripts,
                       extra_patterns=extra_pat)

    def process_logs(self):
        """Process logs for a case"""
        args = self.args
        if not (os.path.exists(args.case_dir) and
                os.path.isdir(args.case_dir)):
            _lgr.fatal("Casee directory does not exist: %s", args.case_dir)
            self.parser.exit(1)
        fname = os.path.join(args.case_dir, args.log_file)
        if not os.path.exists(fname):
            _lgr.fatal("Cannot find log file: %s", fname)
        clog = LogProcessor(
            args.log_file,
            case_dir=osutils.abspath(args.case_dir),
            logs_dir=args.logs_dir)
        clog()
        _lgr.info("%s processed to %s", args.log_file, args.logs_dir)

    def clean_case(self):
        """Clean a case directory"""
        args = self.args
        purge_mesh = args.clean_mesh
        preserve_zero = (not args.clean_zero)
        clean_casedir(args.case_dir,
                      preserve_zero=preserve_zero,
                      purge_mesh=purge_mesh,
                      preserve_extra=args.preserve)

def main():
    """Run caelus command"""
    cmd = CaelusCmd()
    cmd()
