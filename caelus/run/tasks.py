# -*- coding: utf-8 -*-

"""\
Caelus Tasks Manager
----------------------
"""

import os
import glob
import logging
import shutil
from collections import OrderedDict
import six
from ..utils import osutils
from ..utils.struct import Struct
from . import core as run_cmds
from ..post.logs import SolverLog
from ..post.plots import CaelusPlot
from ..config import cmlenv
from ..io import dictfile as cmlio
from .cmd import CaelusCmd
from .hpc_queue import python_execute

_lgr = logging.getLogger(__name__)

class TasksMeta(type):
    """Process available tasks within each Tasks class.

    :class:`TasksMeta` is a metaclass that automates the process of creating a
    lookup table for tasks that have been implemented within the :class:`Tasks`
    and any of its subclasses. Upon initialization of the class, it populates a
    class attribute ``task_map`` that contains a mapping between the task name
    (used in the tasks YAML file) and the corresponding method executed by the
    Tasks class executed.

    """

    def __init__(cls, name, bases, cdict):
        super(TasksMeta, cls).__init__(name, bases, cdict)
        parent = super(cls, cls)
        task_map = (OrderedDict(parent.task_map)
                    if hasattr(parent, "task_map")
                    else OrderedDict())
        for key, value in cdict.items():
            if key.startswith("cmd_"):
                fname = key[4:]
                task_map[fname] = value
        cls.task_map = task_map

@six.add_metaclass(TasksMeta)
class Tasks(object):
    """Caelus Tasks.

    Tasks provides a simple automated workflow interface that provides various
    pre-defined actions via a YAML file interface.

    The tasks are defined as methods with a ``cmd_`` prefix and are
    automaticaly converted to task names. Users can create additional tasks by
    subclassing and adding additional methods with ``cmd_`` prefix. These
    methods accept one argument ``options``, a dictionary containing parameters
    provided by the user for that particular task.

    """

    def __init__(self):
        #: List of tasks that must be performed
        self.tasks = []
        #: File that was used to load tasks
        self.task_file = "None"
        #: Directory where the tasks are to be executed
        self.case_dir = None
        #: Caelus environment used when executing tasks
        self.env = None
        self.dep_job_id = None
        self.task_set_count = 0

    @classmethod
    def load(cls,
             task_file="caelus_tasks.yaml",
             task_node="tasks"):
        """Load tasks from a YAML file.

        If ``exedir is None`` then the execution directory is set to the
        directory where the tasks file is found.

        Args:
            task_file (filename): Path to the YAML file
        """
        self = cls.__new__(cls)
        absfile = osutils.abspath(task_file)
        act_file = Struct.load_yaml(absfile)
        if "tasks" not in act_file:
            raise KeyError("Cannot find tasks list in file: " +
                           task_file)
        self.tasks = act_file[task_node]
        self.task_file = absfile
        _lgr.info("Loaded tasks from: %s", absfile)
        return self

    def __call__(self, case_dir=None, env=None):
        """Execute the tasks

        Args:
            case_dir: Absolute path to the case directory (default: CWD)
            env (CMLEnv): Environment used for the runs
        """
        self._validate_tasks()
        self.case_dir = case_dir or os.getcwd()
        self.case_dir = osutils.abspath(self.case_dir)
        self.env = env or cmlenv.cml_get_version()
        self.dep_job_id = None
        self.task_set_count = 0
        self.used_job_scheduler = False
        act_map = self.task_map
        num_tasks = len(self.tasks)
        _lgr.info("Begin executing tasks in %s", self.case_dir)
        with osutils.set_work_dir(self.case_dir):
            for act in self.tasks:
                for key in act:
                    act_map[key](self, act[key])
        _lgr.info("Successfully executed %d tasks in %s",
                  num_tasks, self.case_dir)

    def _validate_tasks(self):
        """Validate tasks provided by the user before executing"""
        invalid_tasks = []
        for act in self.tasks:
            for key in act:
                if key not in self.task_map:
                    invalid_tasks.append(key)
        if invalid_tasks:
            print("Invalid tasks detected: ")
            for act in invalid_tasks:
                print("  - " + act)
            print("Valid tasks are: ")
            for key, value in self.task_map.items():
                docstr = value.__doc__
                desc = (docstr.strip().split("\n")[0]
                        if docstr else "No help description.")
                print("  - %s - %s"%(key, desc))
            raise RuntimeError("Invalid tasks provided")

    def cmd_run_command(self, options):
        """Execute a Caelus CML binary.

        This method is an interface to :class:`CaelusCmd`
        """
        cml_exe = options.cmd_name
        log_file = options.get("log_file", None)
        cml_cmd = CaelusCmd(cml_exe,
                            casedir=self.case_dir,
                            cml_env=self.env,
                            output_file=log_file)
        parallel = options.get("parallel", False)
        cml_cmd.cml_exe_args = options.get("cmd_args", "")
        cml_cmd.parallel = parallel
        if parallel:
            cml_cmd.num_mpi_ranks = options.get(
                "num_ranks", run_cmds.get_mpi_size(self.case_dir))
            cml_cmd.mpi_extra_args = options.get(
                "mpi_extra_args", "")
        if "queue_settings" in options:
            cml_cmd.runner.update(options["queue_settings"])
        _lgr.info("Executing command: %s", cml_exe)
        job_dep = [self.dep_job_id] if self.dep_job_id else None
        status = cml_cmd(job_dependencies=job_dep)
        self.dep_job_id = cml_cmd.job_id
        self.used_job_scheduler = cml_cmd.runner.is_job_scheduler()
        if status != 0:
            raise RuntimeError("Error executing command: %s"%cml_exe)

    def cmd_run_python(self, options):
        """Execute a python script"""
        pyscript = options.script
        pysfull = osutils.abspath(pyscript)
        pyargs = options.get("script_args", "")
        pylog = options.get("log_file", None)
        log_to_file = options.get("log_to_file", True)
        if not osutils.path_exists(pysfull):
            raise FileNotFoundError("Python file not found: %s", pyscript)
        status = python_execute(
            pysfull, pyargs, env=self.env, log_file=pylog,
            log_to_file=log_to_file)
        if status != 0:
            raise RuntimeError(
                "Error executing python script: %s"%pyscript)

    def cmd_copy_files(self, options):
        """Copy given file(s) to the destination."""
        srcfiles = glob.glob(options.src)
        dest = options.dest

        if not srcfiles:
            raise RuntimeError(
                "Error src pattern %s returns no files", options.src)

        if len(srcfiles) > 1:
            osutils.ensure_directory(dest)

        for srcfile in srcfiles:
            shutil.copy2(srcfile, dest)

    def cmd_copy_tree(self, options):
        """Recursively copy a given directory to the destination."""
        srcdir = options.src
        destdir = options.dest
        ignore_pat = options.get("ignore_patterns", None)
        symlinks = options.get("preserve_symlinks", False)
        ignore_func = None
        if ignore_pat:
            ignore_func = shutil.ignore_patterns(*ignore_pat)
        osutils.copy_tree(srcdir, destdir,
                        symlinks=symlinks, ignore_func=ignore_func)

    def cmd_clean_case(self, options):
        """Clean a case directory"""
        purge_all = options.get("purge_all", False)
        purge_generated = options.get("purge_generated", purge_all)
        remove_zero = options.get("remove_zero", purge_all)
        remove_mesh = options.get("remove_mesh", purge_all)
        remove_times = options.get("remove_time_dirs", purge_generated)
        remove_processors = options.get("remove_processor", purge_generated)
        preserve_extra = options.get("preserve", None)
        remove_extra = options.get("remove_extra", None)
        _lgr.info("Cleaning case directory: %s", self.case_dir)
        run_cmds.clean_casedir(self.case_dir,
                               preserve_zero=(not remove_zero),
                               preserve_times=(not remove_times),
                               preserve_processors=(not remove_processors),
                               purge_mesh=remove_mesh,
                               preserve_extra=preserve_extra)
        if remove_extra:
            osutils.remove_files_dirs(remove_extra, self.case_dir)

    def cmd_process_logs(self, options):
        """Process logs for a case"""
        log_file = options.log_file
        lgfile = os.path.join(self.case_dir, log_file)
        if self.used_job_scheduler and not os.path.exists(lgfile):
            _lgr.info("Skipping process_logs; job submitted on scheduler")
            return
        logs_dir = options.get("logs_directory", "logs")
        _lgr.info("Processing log file: %s", log_file)
        clog = SolverLog(
            case_dir=self.case_dir,
            logs_dir=logs_dir,
            logfile=log_file)
        do_plots = options.get("plot_residuals", None)
        if do_plots:
            plot_file = options.get("residuals_plot_file", "residuals.png")
            fields = options.get("residuals_fields", clog.fields)
            cerrors = options.get("plot_continuity_errors", False)
            plot = CaelusPlot(self.case_dir)
            dname, fname = os.path.split(plot_file)
            plot.plotdir = dname or os.getcwd()
            plot.solver_log = clog
            plot.plot_continuity_errors = cerrors
            plot.plot_residuals_hist(plotfile=fname, fields=fields)
            _lgr.info("Residual time history saved to %s", plot_file)

        try:
            with osutils.set_work_dir(self.case_dir):
                cname = os.path.basename(self.case_dir)
                with open(cname+".foam", 'w') as fh:
                    fh.write(" ")
        except IOError:
            _lgr.warning("Error creating .foam file")

    def cmd_exec_tasks(self, options):
        """Execute another task file"""
        task_file = options.task_file
        casedir = os.path.dirname(task_file)
        tasks = Tasks.load(task_file)
        _lgr.info("Executing tasks from file: %s", task_file)
        tasks(case_dir=casedir, env=self.env)

    def cmd_task_set(self, options):
        """A subset of tasks for grouping"""
        self.task_set_count += 1
        name = options.get("name", "Task set #%d"%self.task_set_count)
        casedir = osutils.abspath(options.case_dir)
        _lgr.info("Executing task set: %s", name)
        tasks = Tasks()
        tasks.tasks = options.tasks
        tasks.task_file = self.task_file
        tasks(case_dir=casedir, env=self.env)

    def cmd_change_inputs(self, options):
        """Change input files in case directory"""
        dictfile_map = cmlio.cml_std_files
        for key, value in options.items():
            obj = None
            if key in dictfile_map:
                cls = dictfile_map[key]
                obj = cls.read_if_present()
            else:
                obj = cmlio.DictFile.read_if_present(filename=key)
            obj.data.merge(value)
            _lgr.info("Updating file: %s", key)
            obj.write()
