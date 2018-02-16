# -*- coding: utf-8 -*-

"""\
Caelus Tasks Manager
----------------------
"""

import os
import logging
import shutil
from collections import OrderedDict
import six
from ..utils import osutils
from ..utils.struct import Struct
from . import core as run_cmds
from ..post.logs import LogProcessor
from ..config.cmlenv import cml_get_version

_lgr = logging.getLogger(__name__)

class TasksMeta(type):
    """Metaclass to track available tasks"""

    def __new__(mcls, name, bases, cdict):
        act_map = OrderedDict()
        for k, value in cdict.items():
            if k.startswith("cmd_"):
                name = k[4:]
                act_map[name] = value
        cdict["task_map"] = act_map
        cls = super(TasksMeta, mcls).__new__(mcls, name, bases, cdict)
        return cls

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
        """Execute tasks """
        self._validate_tasks()
        self.case_dir = case_dir or os.getcwd()
        self.env = env or cml_get_version()
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
        """Execute a Caelus CML program"""
        cml_exe = options.cmd_name
        exe_args = options.get("cmd_args", "")
        exe_base, _ = os.path.splitext(os.path.basename(cml_exe))
        log_file = options.get("log_file", exe_base + ".log")
        parallel = options.get("parallel", False)
        mpi_args = ""
        if parallel:
            num_ranks = options.get("num_ranks",
                                    run_cmds.get_mpi_size(self.case_dir))
            mpi_extra_args = options.get("mpi_extra_args", "")
            ostype = osutils.ostype()
            if ostype == "windows":
                mpi_args = " -localonly %d %s"%(num_ranks, mpi_extra_args)
            else:
                mpi_args = " -np %d %s"%(num_ranks, mpi_extra_args)
            exe_args = " -parallel " + exe_args
        _lgr.info("Executing command: %s", cml_exe)
        status = run_cmds.run_cml_exe(
            cml_exe, env=self.env, logfile=log_file,
            cml_exe_args=exe_args, mpi_args=mpi_args)
        if status != 0:
            raise RuntimeError("Error executing command: %s", cml_exe)

    def cmd_copy_tree(self, options):
        """Recursively copy a given directory to the destination."""
        srcdir = options.src
        destdir = options.dest
        ignore_pat = options.get("ignore_patterns", None)
        symlinks = options.get("preserve_symlinks", False)
        ignore_func = None
        if ignore_pat:
            ignore_func = shutil.ignore_patterns(*ignore_pat)
        shutil.copytree(srcdir, destdir,
                        symlinks=symlinks, ignore=ignore_func)

    def cmd_clean_case(self, options):
        """Clean a case directory"""
        remove_zero = options.get("remove_zero", False)
        remove_mesh = options.get("remove_mesh", False)
        preserve_extra = options.get("preserve", None)
        _lgr.info("Cleaning case directory: %s", self.case_dir)
        run_cmds.clean_casedir(self.case_dir,
                               preserve_zero=(not remove_zero),
                               purge_mesh=remove_mesh,
                               preserve_extra=preserve_extra)

    def cmd_process_logs(self, options):
        """Process logs for a case"""
        log_file = options.log_file
        logs_dir = options.get("logs_directory", "logs")
        _lgr.info("Processing log file: %s", log_file)
        clog = LogProcessor(log_file,
                            case_dir=self.case_dir,
                            logs_dir=logs_dir)
        clog()
