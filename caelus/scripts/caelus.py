# -*- coding: utf-8 -*-

"""\
Caelus command
--------------

"""

import sys
import os
import logging
import shutil

import six

from ..utils import osutils
from ..config.cmlenv import cml_get_version
from .core import CaelusSubCmdScript
from ..run.tasks import Tasks
from ..run.core import clone_case, get_mpi_size, clean_casedir
from ..run import cmd
from ..run.hpc_queue import python_execute
from ..post.logs import SolverLog
from ..post.plots import CaelusPlot, LogWatcher
from ..build.build import get_builder

_lgr = logging.getLogger(__name__)

class CaelusCmd(CaelusSubCmdScript):
    """CLI interface to Caelus Python Library.

    This class provides command-line access to various features implemented
    within the Caelus Python Library without the need for writing custom
    scripts. Common tasks such as cloning a case directory, executing mesh and
    solver executables, automating workflow via tasks, cleaning run
    directories, etc. can be accessed via sub-commands implemented within this
    class.

    Tasks defined:
        - env   - Write shell environment files
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
        cpl_config = subparsers.add_parser(
            "cfg",
            description="dump CPL configuration",
            help="Dump CPL configuration")
        clone = subparsers.add_parser(
            "clone",
            description="Clone a case directory into a new folder.",
            help="clone case directory")
        tasks = subparsers.add_parser(
            "tasks",
            description="Run pre-defined tasks within a case directory "
            "read from a YAML-formatted file.",
            help="run tasks from file")
        run = subparsers.add_parser(
            "run",
            description="Run a Caelus executable in the correct environment",
            help="run a Caelus executable in the correct environment")
        runpy = subparsers.add_parser(
            "runpy",
            description="Run a custom python script with CML and CPL environment",
            help="run a custom python script")
        logs = subparsers.add_parser(
            "logs",
            description="Process logfiles for a Caelus run",
            help="process the solver logs for a Caelus run")
        clean = subparsers.add_parser(
            "clean",
            description="Clean a case directory",
            help="clean case directory")
        build = subparsers.add_parser(
            "build",
            description="Compile Caelus CML",
            help="compile Caelus CML sources")

        # Configuration action
        cpl_config.add_argument(
            '-e', '--expert-mode', action='store_true',
            help="Dump extra options for advanced use")
        cpl_config.add_argument(
            '-f', '--config-file', default=None,
            help="Write to file instead of standard output")
        cpl_config.add_argument(
            '-b', '--no-backup', action='store_true',
            help="Overwrite existing config without saving a backup")
        cpl_config.set_defaults(func=self.write_config)

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
            '-m', '--machinefile', default=None,
            help="machine file for distributed runs (local_mpi only)")
        run.add_argument(
            'cmd_name',
            help="name of the Caelus executable")
        run.add_argument(
            'cmd_args', nargs='*',
            help="additional arguments passed to command")
        run.set_defaults(func=self.run_cmd)

        # Run python script
        runpy.add_argument(
            '-l', '--log-file', default=None,
            help="filename to redirect command output")
        runpy.add_argument(
            '-d', '--case-dir', default=os.getcwd(),
            help="path to the case directory")
        runpy.add_argument(
            'script',
            help="path to the python script")
        runpy.add_argument(
            'script_args', nargs='*',
            help="additional arguments passed to command")
        runpy.set_defaults(func=self.run_python)

        # Logs action
        logs.add_argument(
            '-l', '--logs-dir', default="logs",
            help="directory where logs are output (default: logs)")
        logs.add_argument(
            '-d', '--case-dir', default=os.getcwd(),
            help="path to the case directory")
        logs.add_argument(
            '-p', '--plot-residuals', action='store_true',
            help="generate residual time-history plots")
        logs.add_argument(
            '-c', '--plot-continuity-errors', action='store_true',
            help="plot continuity errors along with field residuals")
        logs.add_argument(
            '-f', '--plot-file', default="residuals.png",
            help="file where plot is saved")
        logs.add_argument(
            '-w', '--watch', action='store_true',
            help="Monitor residuals during a run")
        fields_pat = logs.add_mutually_exclusive_group(required=False)
        fields_pat.add_argument(
            '-i', '--include-fields', default='',
            help="plot residuals for given fields")
        fields_pat.add_argument(
            '-e', '--exclude-fields', default='',
            help="exclude residuals for these fields")
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
            help="remove polyMesh directory (default: no)")
        clean.add_argument(
            '-z', '--clean-zero', action='store_true',
            help="remove 0 directory (default: no)")
        clean.add_argument(
            '-t', '--clean-time-dirs', action='store_true',
            help="remove time directories (default: no)")
        clean.add_argument(
            '-P', '--clean-processors', action='store_true',
            help="clean processor directories (default: no)")
        clean.add_argument(
            '-p', '--preserve', action='append',
            help="shell wildcard patterns of extra files to preserve")
        clean.set_defaults(func=self.clean_case)

        # Build action
        build.add_argument(
            '-l', '--log-file', default=None,
            help="filename to redirect build output")
        build.add_argument(
            '-c', '--clean', action='store_true',
            help="clean CML build")
        build.add_argument(
            '-j', '--jobs', type=int, default=-1,
            help="number of parallel jobs")
        build_dir_pat = build.add_mutually_exclusive_group(required=False)
        build_dir_pat.add_argument(
            '-a', '--all', action='store_true',
            help="Build both project and user directories (default: no)")
        build_dir_pat.add_argument(
            '-p', '--project', action='store_true',
            help="Build Caelus CML project (default: no)")
        build_dir_pat.add_argument(
            '-u', '--user', action='store_true',
            help="Build user project (default: no)")
        build_dir_pat.add_argument(
            '-d', '--source-dir', default=os.getcwd(),
            help="Build sources in path (default: CWD)")
        build.add_argument(
            'build_args', nargs='*',
            help="additional arguments passed to SCons")
        build.set_defaults(func=self.cml_build)

    def write_config(self):
        """Dump the configuration file"""
        args = self.args
        expert_mode = args.expert_mode
        cfg = self.cfg
        log_cfg = cfg.caelus.logging
        if not expert_mode:
            _ = log_cfg.pop('pylogger_options')

        # Backup existing configuration if necessary
        if args.config_file and os.path.exists(args.config_file):
            if not args.no_backup:
                bak_file = osutils.backup_file(args.config_file)
                shutil.copy(args.config_file, bak_file)
                _lgr.info("Existing configuration saved to: %s", bak_file)
            else:
                _lgr.warning("Overwriting CPL existing configuration")

        # Write the latest configuration
        fh = open(args.config_file, 'w') if args.config_file else sys.stdout
        try:
            cfg.write_config(fh)
        finally:
            fh.close()
        if args.config_file:
            _lgr.info("CPL configuration written to file: %s",
                      args.config_file)

    def run_tasks(self):
        """Run tasks"""
        args = self.args
        cenv = cml_get_version()
        _lgr.info("Using CML: %s", cenv)
        task_file = osutils.abspath(args.file)
        dpath = os.path.dirname(task_file)
        if dpath and not os.path.isabs(dpath):
            dpath = osutils.abspath(dpath)
        dpath = dpath or os.getcwd()
        with osutils.set_work_dir(dpath):
            tasks = Tasks.load(os.path.basename(task_file))
            tasks(env=cenv)
        _lgr.info("All tasks executed successfully.")

    def run_cmd(self):
        """Run a Caelus executable"""
        args = self.args
        cenv = cml_get_version()
        cml_cmd = cmd.CaelusCmd(
            args.cmd_name, casedir=args.case_dir,
            cml_env=cenv, output_file=args.log_file)
        cml_cmd.cml_exe_args = ' '.join(args.cmd_args)
        cml_cmd.parallel = args.parallel
        _lgr.info("Using CML: %s", cenv)
        if args.parallel:
            cml_cmd.num_mpi_ranks = get_mpi_size(args.case_dir)
            if args.machinefile is not None:
                if not os.path.exists(args.machinefile):
                    _lgr.error("Cannot find machine file: %s",
                               args.machinefile)
                    self.parser.exit(1)
                if cml_cmd.runner.is_job_scheduler():
                    _lgr.warning("Ignoring machine file with scheduler")
                cml_cmd.runner.machinefile = args.machinefile
            _lgr.info("Executing %s in parallel on %d ranks",
                      args.cmd_name, cml_cmd.num_mpi_ranks)
        else:
            _lgr.info("Executing %s in serial mode", args.cmd_name)

        status = cml_cmd()
        if status != 0:
            _lgr.error("Error executing command; see %s for details",
                       cml_cmd.output_file)
            self.parser.exit(status)
        else:
            _lgr.info("Command executed successfully; see %s for output",
                      cml_cmd.output_file)

    def run_python(self):
        """Run a python executable"""
        args = self.args
        cenv = cml_get_version()
        pyscript = args.script
        pysfull = osutils.abspath(pyscript)
        if not osutils.path_exists(pysfull):
            _lgr.fatal("Cannot find python script: %s", pyscript)
            self.parser.exit(1)

        script_args = ' '.join(args.script_args)
        log_file = args.log_file
        log_to_file = True if log_file else False
        msg_str = "; see %s for details"%log_file if log_to_file else ""
        _lgr.info("Executing python script: %s", pyscript)
        status = python_execute(
            pysfull, script_args, env=cenv,
            log_file=log_file, log_to_file=log_to_file)
        if status != 0:
            _lgr.error("Error executing python script: %s%s",
                       pyscript, msg_str)
            self.parser.exit(status)
        else:
            _lgr.info("Script executed successfully%s", msg_str)

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
        _lgr.info("Cloned case successfully.")

    def process_logs(self):
        """Process logs for a case"""
        args = self.args
        if not (os.path.exists(args.case_dir) and
                os.path.isdir(args.case_dir)):
            _lgr.fatal("Case directory does not exist: %s", args.case_dir)
            self.parser.exit(1)
        fname = os.path.join(args.case_dir, args.log_file)
        include_fields = args.include_fields.split()
        exclude_fields = args.exclude_fields.split()
        cerrors = args.plot_continuity_errors
        if not os.path.exists(fname):
            _lgr.fatal("Cannot find log file: %s", fname)
            self.parser.exit(1)
        if args.watch:
            wlog = LogWatcher(args.log_file, args.case_dir)
            wlog.plot_continuity_errors = cerrors
            if include_fields:
                wlog.plot_fields = include_fields
            if exclude_fields:
                wlog.skip_fields = exclude_fields
            user_exit = wlog()

            # Do not continue if the user aborted using "Ctrl+C"
            if user_exit:
                self.parser.exit(1)

        clog = SolverLog(
            case_dir=osutils.abspath(args.case_dir),
            logs_dir=args.logs_dir,
            logfile=args.log_file)
        _lgr.info("%s processed to %s", args.log_file, args.logs_dir)
        if args.plot_residuals:
            fields = set(clog.fields)
            if exclude_fields:
                fields.difference_update(set(exclude_fields))
            if include_fields:
                fields.intersection_update(set(include_fields))
            plot = CaelusPlot(clog.casedir)
            plot.plot_continuity_errors = cerrors
            dname, fname = os.path.split(args.plot_file)
            plot.plotdir = dname or os.getcwd()
            plot.solver_log = clog
            plot.plot_residuals_hist(plotfile=fname,
                                     fields=fields)
            _lgr.info("Residual time history saved to %s",
                      args.plot_file)

    def clean_case(self):
        """Clean a case directory"""
        args = self.args
        purge_mesh = args.clean_mesh
        preserve_zero = (not args.clean_zero)
        preserve_times = (not args.clean_time_dirs)
        preserve_processors = (not args.clean_processors)
        clean_casedir(args.case_dir,
                      preserve_zero=preserve_zero,
                      preserve_times=preserve_times,
                      preserve_processors=preserve_processors,
                      purge_mesh=purge_mesh,
                      preserve_extra=args.preserve)
        _lgr.info("Cleaned case directory successfully.")

    def cml_build(self):
        """Build CML sources"""
        args = self.args
        build_project = (args.all or args.project)
        build_user = (args.all or args.user)
        build_srcdir = not (build_project or build_user)
        srcdir = osutils.abspath(args.source_dir)
        if build_srcdir and not osutils.path_exists(srcdir):
            _lgr.error("Source directory does not exist: %s", srcdir)
            self.parser.exit(1)

        cenv = cml_get_version()
        _lgr.info("Using CML: %s", cenv)
        builder = get_builder(cenv, args)
        if builder is None:
            self.parser.exit(1)

        prj_successful = True
        if build_project:
            _lgr.info("Compiling project sources")
            builder.build_project_dir()
            if builder.rcode != 0:
                _lgr.error("Compilation failed in project directory. See log for details.")
                prj_successful = False
            else:
                _lgr.info("Project sources compiled successfully.")

        if build_user and prj_successful:
            _lgr.info("Compiling user sources")
            status = builder.build_user_dir()
            if status or builder.rcode != 0:
                _lgr.error("Compilation failed in user directory. See log for details.")
            else:
                _lgr.info("User sources compiled successfully.")
        elif build_user:
            _lgr.warning("Detected incompleted project build; skipping user source compilation.")

        if build_srcdir:
            _lgr.info("Compiling sources in: %s", srcdir)
            builder.build_dir(srcdir)
            if builder.rcode != 0:
                _lgr.error("Compilation failed in directory. See log for details.")
            else:
                _lgr.info("Directory compiled successfully.")
        _lgr.info("Build logs stored in %s", builder.build_log)

def main():
    """Run caelus command"""
    cmd = CaelusCmd()
    cmd()
