# -*- coding: utf-8 -*-

"""\
Caelus Actions Manager
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

class ActionsMeta(type):
    """Metaclass to track available actions"""

    def __new__(mcls, name, bases, cdict):
        act_map = OrderedDict()
        for k, value in cdict.items():
            if k.startswith("cmd_"):
                name = k[4:]
                act_map[name] = value
        cdict["actions_map"] = act_map
        cls = super(ActionsMeta, mcls).__new__(mcls, name, bases, cdict)
        return cls

@six.add_metaclass(ActionsMeta)
class CaelusActions(object):
    """Interface for Caelus Actions Manager"""

    def __init__(self):
        #: List of actions that must be performed
        self.actions = []
        #: File that was used to load actions
        self.actions_file = "None"
        #: Directory where the actions are to be executed
        self.case_dir = None
        #: Caelus environment used when executing actions
        self.env = None

    @classmethod
    def load(cls,
             actions_file="caelus_actions.yaml"):
        """Load actions from a YAML file.

        If ``exedir is None`` then the execution directory is set to the
        directory where the actions file is found.

        Args:
            actions_file (filename): Path to the YAML file
        """
        self = cls.__new__(cls)
        absfile = osutils.abspath(actions_file)
        act_file = Struct.load_yaml(absfile)
        if "actions" not in act_file:
            raise KeyError("Cannot find actions list in file: " +
                           actions_file)
        self.actions = act_file["actions"]
        self.actions_file = absfile
        _lgr.info("Loaded actions from: %s", absfile)
        return self

    def __call__(self, case_dir=None, env=None):
        """Execute actions """
        self._validate_actions()
        self.case_dir = case_dir or os.getcwd()
        self.env = env or cml_get_version()
        act_map = self.actions_map
        num_actions = len(self.actions)
        _lgr.info("Begin executing actions in %s", self.case_dir)
        with osutils.set_work_dir(self.case_dir):
            for act in self.actions:
                for key in act:
                    act_map[key](self, act[key])
        _lgr.info("Successfully executed %d actions in %s",
                  num_actions, self.case_dir)

    def _validate_actions(self):
        """Validate actions provided by the user before executing"""
        invalid_actions = []
        for act in self.actions:
            for key in act:
                if key not in self.actions_map:
                    invalid_actions.append(key)
        if invalid_actions:
            print("Invalid actions detected: ")
            for act in invalid_actions:
                print("  - " + act)
            print("Valid actions are: ")
            for key, value in self.actions_map.items():
                docstr = value.__doc__
                desc = (docstr.strip().split("\n")[0]
                        if docstr else "No help description.")
                print("  - %s - %s"%(key, desc))
            raise RuntimeError("Invalid actions provided")

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
            mpi_args = " -np %d %s"%(num_ranks, mpi_extra_args)
            exe_args = " -parallel " + exe_args
        _lgr.info("Executing command: %s", cml_exe)
        status = run_cmds.run_cml_exe(
            cml_exe, env=self.env, logfile=log_file,
            cml_exe_args=exe_args, mpi_args=mpi_args)
        if status != 0:
            raise RuntimeError("Error executing command: %s", cml_exe)

    def cmd_copy_tree(self, options):
        """General copy action"""
        srcdir = options.src
        destdir = options.dest
        ignore_pat = options.get("ignore_patters", None)
        ignore_func = None
        if ignore_pat:
            ignore_func = shutil.ignore_patterns(*ignore_pat)
        shutil.copytree(srcdir, destdir, ignore=ignore_func)

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
