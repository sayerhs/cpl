# -*- coding: utf-8 -*-

"""\
Caelus command
--------------

"""

import os
import logging
from collections import OrderedDict
from ..utils import osutils
from ..config.cmlenv import cml_get_version
from .core import CaelusSubCmdScript
from ..run.tasks import Tasks
from ..run.core import clone_case, get_mpi_size, run_cml_exe, clean_casedir
from ..post.logs import LogProcessor

_lgr = logging.getLogger(__name__)

def populate_environment(cenv):
    """Populate environment used for sourcing in shells"""

    ostype = osutils.ostype()
    varnames = """project project_dir caelus_project_dir
        build_option external_dir mpi_buffer_size
        opal_prefix""".upper().split()

    env = OrderedDict()
    env["PROJECT_NAME"] = "Caelus"
    env["PROJECT_VERSION"] = cenv.version
    env["PROJECT_VER"] = cenv.version

    for evar in varnames:
        env[evar] = cenv.environ[evar]

    env["PATH"] = (
        cenv.bin_dir + os.pathsep +
        cenv.mpi_bindir + os.pathsep + "$PATH")
    lib_path = ("LD_LIBRARY_PATH" if ostype != "darwin"
                else "DYLD_FALLBACK_LIBRARY_PATH")
    env[lib_path] = (
        cenv.lib_dir + os.pathsep +
        cenv.mpi_libdir + os.pathsep +
        "$%s"%lib_path)
    env["OMP"] = False
    env["MPI_LIB_PATH"] = cenv.mpi_libdir
    env["BIN_PLATFORM_INSTALL"] = cenv.bin_dir
    env["LIB_PLATFORM_INSTALL"] = cenv.lib_dir
    env["SCONSFLAGS"] = "--site-dir=%s/site_scons"%cenv.project_dir

    env["LIB_SRC"] = os.path.normpath(os.path.join(
        cenv.project_dir, "src", "libraries"))
    env["CAELUS_APP"] = os.path.normpath(os.path.join(
        cenv.project_dir, "src", "applications"))
    env["CAELUS_SOLVERS"] = os.path.normpath(os.path.join(
        cenv.project_dir, "src", "applications", "solvers"))
    env["CAELUS_UTILITIES"] = os.path.normpath(os.path.join(
        cenv.project_dir, "src", "applications", "utilities"))
    env["CAELUS_TUTORIALS"] = os.path.normpath(os.path.join(
        cenv.project_dir, "tutorials"))
    return env

def write_unix_env(env):
    """Write out unix environment files"""
    bash_fmt = 'export %s="%s"\n'
    csh_fmt = 'setenv %s "%s"\n'
    with open("caelus-bashrc", 'w') as fh:
        fh.write("#!/bin/bash\n")
        fh.write("#\n# Bash configuration file for %s\n\n"%env["PROJECT"])
        for key, value in env.items():
            fh.write(bash_fmt%(key, value))
    _lgr.info("Bash environment file written to: %s",
              os.path.join(os.getcwd(), "caelus-bashrc"))
    with open("caelus-cshrc", 'w') as fh:
        fh.write("#!/bin/csh\n")
        fh.write("#\n# csh configuration file for %s\n\n"%env["PROJECT"])
        for key, value in env.items():
            fh.write(csh_fmt%(key, value))
    _lgr.info("Csh environment file written to: %s",
              os.path.join(os.getcwd(), "caelus-cshrc"))

def write_windows_env(env):
    """Write out unix environment files"""
    header = """
REM Caelus run environment
@echo off

"""
    cmd_fmt = '@set %s=%s\n'
    with open("caelus-environment.cmd", 'w') as fh:
        fh.write(header)
        for key, value in env.items():
            fh.write(cmd_fmt%(key, value))
    _lgr.info("Environment file written to: %s",
              os.path.join(os.getcwd(), "caelus-environment.cmd"))

class CaelusCmd(CaelusSubCmdScript):
    """CLI interface to Caelus Python Library.

    This class provides command-line access to various features implemented
    within the Caelus Python Library without the need for writing custom
    scripts. Common tasks such as cloning a case directory, executing mesh and
    solver executables, automating workflow via tasks, cleaning run
    directories, etc. can be accessed via sub-commands implemented within this
    class.

    Tasks defined:
        - clone - Clone a case directory
        - tasks - Execute workflow from a Tasks file
        - run   - Run a Caelus executable in serial or parallel
        - logs  - Process a log file and extract residuals
        - clean - Clean a case directory
    """

    description = "Caelus Python Utility Interface"

    def cli_options(self):
        """Setup sub-commands for the Caelus application"""
        super(CaelusCmd, self).cli_options()
        subparsers = self.subparsers
        env = subparsers.add_parser(
            "env",
            description="Write environment variables that can be "
            "sourced into the SHELL environment",
            help="write shell environment file")
        clone = subparsers.add_parser(
            "clone",
            description="Clone a case directory into a new folder.",
            help="clone case directory")
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
            help="process the solver logs for a Caelus run")
        clean = subparsers.add_parser(
            "clean",
            description="Clean a case directory",
            help="clean case directory")

        # Env action
        env.add_argument(
            '-d', '--write-dir', default=None,
            help="Path where the environment files are written")
        env.set_defaults(func=self.write_env)

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
            help="file containing tasks to execute (caelus_tasks.yaml)")
        tasks.set_defaults(func=self.run_tasks)

        # Run action
        run.add_argument(
            '-p', '--parallel', action='store_true',
            help="run in parallel")
        run.add_argument(
            '-l', '--log-file', default=None,
            help="filename to redirect command output")
        run.add_argument(
            '-d', '--case-dir', default=os.getcwd(),
            help="path to the case directory")
        run.add_argument(
            'cmd_name',
            help="name of the Caelus executable")
        run.add_argument(
            'cmd_args', nargs='*',
            help="additional arguments passed to command")
        run.set_defaults(func=self.run_cmd)

        # Logs action
        logs.add_argument(
            '-l', '--logs-dir', default="logs",
            help="directory where logs are output (default: logs)")
        logs.add_argument(
            '-d', '--case-dir', default=os.getcwd(),
            help="path to the case directory")
        logs.add_argument(
            "log_file",
            help="log file (e.g., simpleSolver.log)")
        logs.set_defaults(func=self.process_logs)

        # Clean action
        clean.add_argument(
            '-d', '--case-dir', default=os.getcwd(),
            help="path to the case directory")
        clean.add_argument(
            '-m', '--clean-mesh', action='store_true',
            help="remove polyMesh directory")
        clean.add_argument(
            '-z', '--clean-zero', action='store_true',
            help="remove 0 directory")
        clean.add_argument(
            '-p', '--preserve', action='append',
            help="shell wildcard patterns of extra files to preserve")
        clean.set_defaults(func=self.clean_case)

    def write_env(self):
        """Write out the environment file"""
        args = self.args
        write_dir = args.write_dir
        cenv = cml_get_version()
        if not (write_dir and
                os.path.exists(write_dir) and
                os.path.isdir(write_dir)):
            _lgr.error("Directory does not exist: %s", write_dir)
            self.parser.exit(1)
        if write_dir is None:
            write_dir = os.path.join(
                cenv.project_dir, "etc")
        with osutils.set_work_dir(write_dir):
            env = populate_environment(cenv)
            if osutils.ostype() == "windows":
                write_windows_env(env)
            else:
                write_unix_env(env)

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
