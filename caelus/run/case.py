# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, protected-acess, bare-except

"""\
CML Simulation
--------------

This module defines :class:`CMLSimulation` that provides a pythonic interface
to detail with a CML case directory. In addition to implementing methods to
perform actions, it also tracks the state of the analysis at any given time.

The module also provides an abstract interface :class:`CMLSimCollection` that
provides basic infrastructure to manage and manipulate a collection of
simulations as a group.
"""

import os
import logging
from collections import Mapping
import json
import fnmatch
import abc
import six

import numpy as np

from ..config import cmlenv
from ..utils import osutils
from ..utils.tojson import JSONSerializer
from ..utils.pyutils import import_script
from ..post.logs import SolverLog
from ..io.caelusdict import CaelusDict
from ..io import dictfile as cmlio
from . import core as rcore
from . import tasks
from .cmd import CaelusCmd
from .udf import SimUDFBase

_lgr = logging.getLogger(__name__)

class CMLSimMeta(type):
    """Decorator to add dictfile accessors to CMLSimulation"""

    def __init__(cls, name, bases, cdict):
        super(CMLSimMeta, cls).__init__(name, bases, cdict)
        if "_dictfile_attrs" in cdict:
            cls.add_dictfile_attrs(cdict["_dictfile_attrs"])

    def add_dictfile_attrs(cls, attrmap):
        """Create getters for dictionary file objects"""
        for key, value in attrmap.items():
            cls.process_attr(key, value)

    def process_attr(cls, key, value):
        """Create the attribute"""
        doc = "Return %s instance for this case"%key
        varname = "_"+key
        def getter(self):
            if hasattr(self, varname):
                return getattr(self, varname)

            obj = value.read_if_present(casedir=self.casedir)
            self._dicts_accessed.append(obj)
            setattr(self, varname, obj)
            return obj
        setattr(cls, key, property(getter, doc=doc))

@six.add_metaclass(CMLSimMeta)
class CMLSimulation(JSONSerializer):
    """Pythonic interface to CML/OpenFOAM simulation

    This class defines the notion of an analysis. It provides methods to
    interact with an analysis directory from within python, and provides basic
    infrastructure to track the status of the simulation.

    After successful :meth:`setup`, the simulation moves through a series of
    stages, that can be queried via :meth:`status` method:

      =========== =================================================
      Status      Description
      =========== =================================================
      Setup       Case setup successfully
      Prepped     Pre-processing completed
      Submitted   Solver initialized
      Running     Solver is running
      Solved      Solve has completed
      DONE        Post-processing completed
      FAILED      Some action failed
      =========== =================================================
    """
    _dictfile_attrs = cmlio.cml_std_files

    _json_public_ = ("name run_config run_flags "
                     "_solver _logfile "
                     "job_ids ".split())

    #: Name of the task file for this case
    task_file = "caelus_tasks.yaml"

    def __init__(self,
                 case_name,
                 cml_env=None,
                 basedir=None,
                 parent=None):
        """
        Args:
            case_name (str): Unique identifier for the case
            env (CMLEnv): CML environment used to setup/run the case
            basedir (path): Location where the case is located/created
            parent (CMLSimCollection): Instance of the group manager
        """
        #: CML environment used to run this case
        self.env = cml_env or cmlenv.cml_get_version()
        #: Unique name for this case
        self.name = case_name
        #: Root directory containing the case
        self.basedir = osutils.abspath(basedir) if basedir else os.getcwd()
        #: Absolute path to the case directory
        self.casedir = os.path.join(self.basedir, self.name)
        #: Instance of CMLSimCollection if part of a larger set
        self.parent = parent

        #: Keep track of files accessed
        self._dicts_accessed = []

        #: Dictionary containing run configuration (internal use only)
        self.run_config = CaelusDict()

        #: User-defined customization class
        self.udf = SimUDFBase()

        #: Dictionary tracking status (internal use only)
        self.run_flags = CaelusDict(
            updated=False,
            prepped=False,
            solve_submitted=False,
            solve_completed=False,
            post_done=False,
            failed=False
        )
        #: Job IDs for SLURM/PBS jobs (internal use only)
        self.job_ids = []

    @classmethod
    def load(cls, env=None, casedir=None, parent=None, json_file=None):
        """Loads a previously setup case from persistence file"""
        cdir = osutils.abspath(casedir) if casedir else  os.getcwd()
        jfile = json_file or cls.json_file()
        jfile = osutils.abspath(os.path.join(cdir, jfile))
        data = json.load(open(jfile), object_pairs_hook=CaelusDict)

        self = cls.__new__(cls)
        self.env = env or cmlenv.cml_get_version()
        self.casedir = cdir
        self.basedir = os.path.dirname(self.casedir)
        self.parent = parent
        self.udf = SimUDFBase()
        self._dicts_accessed = []
        for k in self._json_public_:
            setattr(self, k, data.get(k, None))
        return self

    def clone(self,
              template_dir,
              copy_polymesh=True,
              copy_zero=True,
              copy_scripts=True,
              extra_patterns=None,
              clean_if_present=False):
        """Create the case directory from a given template

        Args:
            template_dir (path): Case directory to be cloned
            copy_polymesh (bool): Copy contents of constant/polyMesh to new case
            copy_zero (bool): Copy time=0 directory to new case
            copy_scripts (bool): Copy python and YAML files
            extra_patterns (list): List of shell wildcard patterns for copying
            clean_if_present (bool): Overwrite existing case

        Raises:
            IOError: If ``casedir`` exists and ``clean_if_present`` is False
        """
        if osutils.path_exists(self.casedir) and not clean_if_present:
            raise IOError("Refusing to overwrite existing case: %s",
                          self.casedir)
        rcore.clone_case(self.casedir, template_dir,
                         copy_polymesh, copy_zero, copy_scripts,
                         extra_patterns)

    def clean(self,
              preserve_extra=None,
              preserve_polymesh=True,
              preserve_zero=True,
              preserve_times=False,
              preserve_processors=False):
        """Clean an existing case directory.

        Args:
            preserve_extra (list): List of shell wildcard patterns to preserve
            preserve_polymesh (bool): If False, purges polyMesh directory
            preserve_zero (bool): If False, removes the 0 directory
            preserve_times (bool): If False, removes the time directories
            preserve_processors (bool): If False, removes processor directories
        """
        rcore.clean_casedir(
            self.casedir,
            preserve_extra=preserve_extra,
            preserve_zero=preserve_zero,
            preserve_times=preserve_times,
            preserve_processors=preserve_processors,
            purge_mesh=(not preserve_polymesh))

    def update(self, input_mods=None):
        """Update the input files within a case directory

        Args:
            input_mods (CaelusDict): Dictionary with changes
        """
        with osutils.set_work_dir(self.casedir):
            if input_mods is not None:
                self._update_input_files(input_mods)
            elif hasattr(self.run_config, "change_inputs"):
                self._update_input_files(self.run_config.change_inputs)
            self._write_modified_files()
            # Mark as updated, and possibly needs to be re-prepped
            self.run_flags.updated = True
            self.run_flags.prepped = False

    def prep_case(self, prep_tasks=None, force=False):
        """Execute pre-processing tasks for this case

        If not tasks are provided, then uses the section ``prep`` from
        ``run_configuration`` that was passed during the setup phase.

        Args:
            prep_tasks (list): List of tasks for Tasks
            force (bool): Force prep again if already run

        """
        skip_prep = self.udf.case_prep_prologue(case=self, force=force)

        if not skip_prep:
            self._prep_case_default(prep_tasks, force)

        self.udf.case_prep_epilogue(case=self, force=force)

    def _prep_case_default(self, prep_tasks=None, force=False):
        """Execute pre-processing tasks for this case

        If not tasks are provided, then uses the section ``prep`` from
        ``run_configuration`` that was passed during the setup phase.

        Args:
            prep_tasks (list): List of tasks for Tasks
            force (bool): Force prep again if already run

        """
        if self.run_flags.prepped and not force:
            _lgr.warning("%s: Detected previous prep, skipping",
                         self.name)
            return
        if not self.run_flags.updated:
            self.update()
        _lgr.info("Executing pre-processing tasks for case: %s",
                  self.name)
        tasklist = prep_tasks or self.run_config.get("prep", None)
        try:
            if tasklist:
                ctasks = tasks.Tasks()
                ctasks.tasks = tasklist
                ctasks(case_dir=self.casedir, env=self.env)
            # Decompose the case if necessary
            self.decompose_case(ctasks.dep_job_id, force)
            self.run_flags.prepped = True
        except:
            _lgr.exception("Error encountered during prep for %s",
                           self.name)
            self.run_flags.failed = True


    def decompose_case(self, dep_job_id=None, force=False):
        """Decompose case if necessary

        Args:
            dep_job_id (int): Job ID to wait for
            force (bool): Force rerun of decomposition tasks
        """
        num_ranks = self.run_config.get("num_ranks", 1)
        if num_ranks < 2:
            return
        num_proc_dirs = rcore.get_mpi_size(self.casedir)
        if (num_ranks != num_proc_dirs) or force:
            with osutils.set_work_dir(self.casedir):
                decomp = self.decomposeParDict
                decomp.numberOfSubdomains = num_ranks
                decomp.write()

                cml_cmd = CaelusCmd(
                    "decomposePar",
                    casedir=self.casedir,
                    cml_env=self.env,
                    output_file="decomposePar.log")
                cml_cmd.cml_exe_args = "-force"
                _lgr.info("Decomposing case: %s", self.name)
                job_dep = [dep_job_id] if dep_job_id else None
                status = cml_cmd(job_dependencies=job_dep)
                if cml_cmd.job_id:
                    self.job_ids.append(cml_cmd.job_id)
                if status != 0:
                    _lgr.fatal("Error encountered during decomposePar for: %s",
                               self.name)
                    self.run_flags.failed = True

    def solve(self, force=False):
        """Execute solve for this case

        Args:
            force (bool): Force resubmit even if previously submitted
        """
        rflags = self.run_flags
        if rflags.solve_submitted and not force:
            _lgr.info("%s: Detected previous solve, skipping",
                      self.name)
            return

        if not rflags.prepped:
            self.prep_case()
        solve_opts = self.run_config.get("solve", None)
        if not solve_opts:
            raise KeyError("Cannot find solve settings for case: %s"%
                           self.name)
        status = 0
        if isinstance(solve_opts, (list,)):
            for sopt in solve_opts:
                solvstat = self._run_solver(sopt)
                status = max(solvstat, status)
        elif isinstance(solve_opts, Mapping):
            status = self._run_solver(solve_opts)
        else:
            sopt = dict(
                solver=solve_opts,
                solver_args="")
            status = self._run_solver(sopt)
        if status == 0:
            self.run_flags.solve_submitted = True

    def _run_solver(self, sopts):
        """Helper method to run the solver"""
        dep_job_id = self.job_ids[-1] if self.job_ids else None
        self.solver = sopts["solver"]
        log_file = sopts.get("log_file", None)
        if log_file is not None:
            self._logfile = log_file
        solver_args = sopts.get("solver_args", "")
        cml_cmd = CaelusCmd(
            self.solver,
            casedir=self.casedir,
            cml_env=self.env,
            output_file=log_file)
        cml_cmd.cml_exe_args = solver_args
        cml_cmd.num_mpi_ranks = self.run_config.get("num_ranks", 1)
        cml_cmd.mpi_extra_args = self.run_config.get(
            "mpi_extra_args", "")
        if "queue_settings" in self.run_config:
            cml_cmd.runner.update(self.run_config["queue_settings"])
        _lgr.info("Submitting solver (%s) for case: %s",
                  self.solver, self.name)
        status = cml_cmd(job_dependencies=dep_job_id)
        if cml_cmd.job_id:
            self.job_ids.append(cml_cmd.job_id)
        if status != 0:
            _lgr.error("Error encountered running %s for: %s",
                       self.solver, self.name)
            self.run_flags.failed = True
        return status

    def post_case(self, post_tasks=None, force=False):
        """Execute post-processing tasks for this case"""
        skip_post = self.udf.case_post_prologue(case=self, force=force)

        if not skip_post:
            self._post_case_default(post_tasks, force)

        self.udf.case_post_epilogue(case=self, force=force)

    def _post_case_default(self, post_tasks=None, force=False):
        """Execute post-processing tasks for this case"""
        if self.run_flags.post_done and not force:
            _lgr.info("%s: Detected previous post-processing, skipping",
                      self.name)
            return

        if not self.run_flags.solve_submitted:
            _lgr.warning("%s: No previous solve detected, skipping post",
                         self.name)
            return

        clog = self.case_log()
        if clog is None:
            _lgr.warning("%s: Solve has not started, skipping post",
                         self.name)
            return
        if not clog.solve_completed:
            _lgr.warning("%s: Solve was not completed, skipping post",
                         self.name)
            return

        _lgr.info("Executing post-processing tasks for case: %s",
                  self.name)
        self.run_flags.solve_completed = clog.solve_completed
        self.reconstruct_case()
        tasklist = post_tasks or self.run_config.get("post", None)
        try:
            if tasklist:
                ctasks = tasks.Tasks()
                ctasks.tasks = tasklist
                ctasks(case_dir=self.casedir, env=self.env)
            self.run_flags.post_done = True
        except:
            _lgr.exception("Error occurred during post for: %s", self.name)
            self.run_flags.failed = True

    def reconstruct_case(self):
        """Reconstruct a parallel case"""
        rconf = self.run_config
        num_ranks = rconf.get("num_ranks", 1)
        dorecon = rconf.get("reconstruct", False)
        if dorecon and (num_ranks > 1):
            _lgr.info("Reconstructing parallel run in case: %s",
                      self.name)
            cml_cmd = CaelusCmd(
                "reconstructPar",
                casedir=self.casedir,
                cml_env=self.env,
                output_file="reconstructPar.log")
            cml_cmd.cml_exe_args = "-latestTime"
            _lgr.info("Reconstructing case: %s", self.name)
            status = cml_cmd(job_dependencies=None)
            if status != 0:
                _lgr.fatal("Error encountered during reconstruction")
                self.run_flags.failed = True

    def status(self):
        """Determine status of the run

        Returns:
            str: Status of the run as a string
        """
        run_flags = self.run_flags
        status_list = """failed post completed running submitted prep setup""".split()
        status_names = """FAILED DONE Solved Running Submitted Prepped Setup""".split()
        status_flags = {}
        for k in status_list:
            status_flags[k] = False
        status_flags["post"] = run_flags["post_done"]
        status_flags["prep"] = run_flags["prepped"]
        status_flags["setup"] = run_flags["updated"]
        status_flags["submitted"] = run_flags["solve_submitted"]
        status_flags["failed"] = run_flags["failed"]
        if (not status_flags["failed"]
            and status_flags["submitted"]
            and not status_flags["completed"]):
            try:
                clog = self.case_log()
                if clog is not None:
                    if clog.solve_completed:
                        run_flags["solve_completed"] = clog.solve_completed
                        status_flags["completed"] = clog.solve_completed
                    elif clog.failed:
                        status_flags["failed"] = True
                        status_flags["running"] = False
                        status_flags["completed"] = False
                    else:
                        status_flags["running"] = True
            except:
                status_flags["running"] = False
                status_flags["completed"] = False
                status_flags["failed"] = True
        for i, k in enumerate(status_list):
            if status_flags[k]:
                return status_names[i]

    def _update_input_files(self, input_mods):
        """Internal function to update input files"""
        _lgr.info("Updating input files for %s", self.name)
        for fname, mods in input_mods.items():
            if hasattr(self, fname):
                obj = getattr(self, fname)
                obj.merge(mods)
            else:
                obj = self.get_input_dict(fname)
                obj.data.merge(mods)

    def _write_modified_files(self):
        """Helper function to write out modifications"""
        _lgr.info("Saving modified files for %s", self.name)
        for obj in self._dicts_accessed:
            _lgr.info("Updating %s/%s", self.name, obj.filename)
            obj.write()

    @property
    def solver(self):
        """Return the solver used for this case"""
        return getattr(self, "_solver", None)

    @solver.setter
    def solver(self, value):
        setattr(self, "_solver", value)

    @property
    def logfile(self):
        """The log file for the solver"""
        logname = None
        if getattr(self, "_logfile", None):
            logname = getattr(self, "_logfile")
        elif self.solver is not None:
            logname = "%s.log"%self.solver
        else:
            raise ValueError("Cannot determine log file for case: %s"%
                             self.name)
        setattr(self, "_logfile", logname)
        return self._logfile

    @logfile.setter
    def logfile(self, value):
        setattr(self, "_logfile", value)

    def case_log(self, force_reload=False):
        """Return a SolverLog instance for this case"""
        if hasattr(self, "_logs") and not force_reload:
            return getattr(self, "_logs")

        logfile = os.path.join(self.casedir, self.logfile)
        if not osutils.path_exists(logfile):
            return None

        with osutils.set_work_dir(self.casedir):
            clog = SolverLog(
                case_dir=self.casedir,
                force_reload=force_reload,
                logfile=self.logfile)
            setattr(self, "_logs", clog)
            return clog

    def run_tasks(self, task_file=None):
        """Run tasks within case directory using the tasks file"""
        tfile = task_file or self.task_file
        if not osutils.path_exists(tfile):
            raise IOError("Cannot file task file for case: %s"%self.name)
        with osutils.set_work_dir(self.casedir):
            ctasks = tasks.Tasks.load(tfile)
            ctasks(env=self.env)

    def get_input_dict(self, dictname):
        """Return a CPL instance of the input file

        For standard input files, prefer to use the accessors directly instead
        of this method. For example, case.controlDict,
        case.turbulenceProperties, etc.

        Args:
            dictname (str): File name relative to case directory
        """
        with osutils.set_work_dir(self.casedir):
            cdict = cmlio.DictFile.load(dictname)
            self._dicts_accessed.append(cdict)
            return cdict

    def save_state(self, **kwargs):
        """Dump persistence file in JSON format"""
        with osutils.set_work_dir(self.casedir):
            with open(self.json_file(), 'w') as fh:
                json.dump(self.to_json(), fh,
                          cls=self._json_dumper_, **kwargs)

    def __repr__(self):
        return "<%s: %s>"%(self.__class__.__name__, self.name)


@six.add_metaclass(abc.ABCMeta)
class CMLSimCollection(JSONSerializer):
    """Interface representing a collection of cases

    Implementations must implement :meth:`setup` that provides a concrete
    implementation of how the case is setup (either from a template or
    otherwise).

    Provides :meth:`prep`, :meth:`solve`, :meth:`post`, and :meth:`status` to
    interact with the collection as a whole. Prep, solve, and post can accept a
    list of shell-style wildcard patterns that will restrict the actions to
    matching cases only.
    """

    def __init__(self, name, env=None, basedir=None):
        """
        Args:
            name (str): Unique name for this parametric run
            env (CMLEnv): CML excution environment
            basedir (path): Path where analysis directory is created
        """
        #: Unique name for this parametric collection of cases
        self.name = name
        bdir = basedir or os.getcwd()
        #: Location where parametric run setup is located
        self.basedir = osutils.abspath(bdir)
        #: Location of the parametric run
        self.casedir = os.path.join(self.basedir, self.name)
        if osutils.path_exists(self.casedir):
            _lgr.error("Parametric run directory exists. Aborting")
            raise FileExistsError(
                "Cannot overwrite existing directory: %s"%
                self.casedir)
        self._nested_file_guard(self.basedir)

        #: CML execution environment
        self.env = env or cmlenv.cml_get_version()

        #: List of CMLSimulation instances
        self.cases = []
        #: Names of cases
        self.case_names = []

        #: UDF function
        self.udf = SimUDFBase()

    @classmethod
    def simulation_class(cls):
        """Concrete instance of a Simulation

        Default is :class:`CMLSimulation`
        """
        return CMLSimulation

    @classmethod
    def udf_instance(cls, custom_script=None, udf_params=None):
        """Return a UDF instance"""
        if custom_script is None:
            return SimUDFBase()

        udfpar = udf_params or CaelusDict()
        udf_module = import_script(osutils.abspath(custom_script))
        return getattr(udf_module, "get_udf_instance")(udfpar)

    @classmethod
    def load(cls, env=None, casedir=None, json_file=None):
        """Reload a persisted analysis group

        Args:
            env (CMLEnv): Environment for the analysis
            casedir (path): Path to the case directory
            json_file (filename): Persistence information
        """
        cdir = osutils.abspath(casedir) if casedir else  os.getcwd()
        jfile = json_file or cls.json_file()
        jfile = osutils.abspath(os.path.join(cdir, jfile))
        data = json.load(open(jfile), object_pairs_hook=CaelusDict)

        self = cls.__new__(cls)
        self.env = env or cmlenv.cml_get_version()
        self.casedir = cdir
        self.basedir = os.path.dirname(self.casedir)
        for k in self._json_public_:
            setattr(self, k, data.get(k, None))

        self.udf = cls.udf_instance(self.udf_script, self.udf_params)

        self.cases = [
            self.simulation_class().load(
                env=self.env, casedir=os.path.join(self.casedir, cname),
                parent=self)
            for cname in self.case_names
        ]
        for case in self.cases:
            case.udf = self.udf

        self.udf.sim_init_udf(simcoll=self, is_reload=True)
        return self

    @abc.abstractmethod
    def setup(self):
        """Logic to set up the analysis"""

    def prep(self, cnames=None, force=False):
        """Run prep actions on the cases

        Args:
            cnames (list): Shell-style wildcard patterns
            force (bool): Force rerun
        """
        cases = self.filter_cases(cnames) if cnames else self.cases
        for c in cases:
            c.prep_case(force=force)
            c.save_state()

    def solve(self, cnames=None, force=False):
        """Run solve actions on the cases

        Args:
            cnames (list): Shell-style wildcard patterns
            force (bool): Force rerun
        """
        cases = self.filter_cases(cnames) if cnames else self.cases
        for c in cases:
            c.solve(force=force)
            c.save_state()

    def post(self, cnames=None, force=False):
        """Run post-processing tasks on the cases

        Args:
            cnames (list): Shell-style wildcard patterns
            force (bool): Force rerun
        """
        cases = self.filter_cases(cnames) if cnames else self.cases
        for c in cases:
            c.post_case(force=force)
            c.save_state()

    def status(self):
        """Return the status of the runs

        Yields:
            tuple: (name, status) for each case
        """
        for c in self.cases:
            yield (c.name, c.status())

    def save_state(self, **kwargs):
        """Dump persistence file in JSON format"""
        with osutils.set_work_dir(self.casedir):
            self.udf.sim_epilogue(self)
            with open(self.json_file(), 'w') as fh:
                json.dump(self.to_json(), fh,
                          cls=self._json_dumper_, **kwargs)
            for c in self.cases:
                c.save_state(**kwargs)

    def filter_cases(self, patterns):
        """Filter the cases based on a list of patterns

        The patterns are shell-style wildcard strings to match case directory
        names.

        Args:
            patterns (list): A list of one or more patterns
        """
        casemap = CaelusDict(zip(self.case_names, self.cases))
        for pat in patterns:
            cnames = casemap.keys()
            matches = fnmatch.filter(cnames, pat)
            for m in matches:
                c = casemap.pop(m)
                yield c

    def _nested_file_guard(self, basedir):
        """Check for nested simulation collections"""
        fname = self.json_file()
        wdir = basedir
        parent = os.path.dirname(wdir)
        json_file = None
        while (parent != wdir):
            jfile = os.path.join(wdir, fname)
            if os.path.exists(jfile):
                json_file = jfile
                break
            wdir = parent
            parent = os.path.dirname(wdir)
        if json_file is not None:
            _lgr.error("Detected nested analysis directories. Aborting setup")
            raise FileExistsError("Refusing to create nested analysis directories")

    @property
    def udf_script(self):
        """Return the UDF script"""
        return None

    @property
    def udf_params(self):
        """Return the parameters for UDF script"""
        return None

    def __repr__(self):
        return "<%s: %s (%d cases)>"%(
            self.__class__.__name__,
            self.name, len(self.cases))
