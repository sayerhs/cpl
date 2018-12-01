# -*- coding: utf-8 -*-

"""\
Caelus Log Analyzer
-------------------

This module provides utilities to parse and extract information from solver
outputs (log files) that can be used to monitor and analyze the convergence of
runs. It implements the :class:`SolverLog` class that can be used to access
time histories of residuals for various fields of interest.

Example:
    >>> logs = SolverLog()
    >>> print ("Available fields: ", logs.fields)
    >>> ux_residuals = logs.residual("Ux")

The actual extraction of the logs is performed by :class:`LogProcessor` which
uses regular expressions to match lines of interest and convert them into
tabular files suitable for loading with ``numpy.loadtxt`` or
``pandas.read_table``.
"""

import os
import logging
from os.path import join
from collections import OrderedDict
import json

import numpy as np

from ..utils import osutils
from ..utils.coroutines import coroutine, grep

_lgr = logging.getLogger(__name__)

class LogProcessor(object):
    """Process the log file and extract information for analysis.

    This is a low-level utility to parse log files and extract information
    using regular expressions from the log file. Users should interact with
    solver output using the :class:`SolverLog` class.
    """

    # Regular expressions that match common lines of interest in a CML solver
    # output
    expressions = dict(
        time=r"^Time = (\S+)",
        courant=r"^Courant Number mean: (\S+) max: (\S+)",
        residual=r"(\S+): *Solving for (\S+), Initial residual = (\S+), Final residual = (\S+), No Iterations (\S+)",
        bounding=r"^bounding (\S+), min:\s*(\S+)\s+max:\s*(\S+)\s+average:\s*(\S+)",
        continuity=r"time step continuity errors : sum local = (\S+), global = (\S+), cumulative = (\S+)",
        exec_time=r"ExecutionTime = (\S+) s  ClockTime = (\S+) s",
        convergence=r"(\S+) solution converged in (\S+) iterations",
        completion=r"^End$",
        exiting="^.*(CAELUS|OpenFOAM).*exiting",
        fatal_error="^.*(CAELUS|OpenFOAM).*FATAL ERROR"
    )

    def __init__(self, logfile,
                 case_dir=None,
                 logs_dir="logs"):
        """
        Args:
            logfile (str): Name of the Caelus log file
            casedir (path): Path to the case directory (default: cwd)

            logs_dir (path): Relative path to the directory where logs
                             are written
        """
        #: Absolute path to the case directory
        self.case_dir = case_dir or os.getcwd()
        #: Absolute path to the directory containing processed logs
        self.logs_dir = osutils.ensure_directory(
            join(self.case_dir, logs_dir))
        #: User-supplied log file (relative to case directory)
        self.logfile = join(self.case_dir, logfile)

        #: Track the latest time that was processed by the utility
        self.time = 0.0

        #: Time as a string (for output)
        self.time_str = "0"

        #: (variable, subIteration) pairs tracking the number of predictor
        #: subIterations for each flow variable
        self.subiter_map = {}

        #: Open file handles for the residual outputs
        self.res_files = OrderedDict()
        #: Open file handles for bounding outputs
        self.bound_files = OrderedDict()

        #: List of user-defined rules to process
        self._user_rules = []

        #: Extra actions for pre-defined expressions
        self._extra_rules = {}

        #: Flag indicating convergence message in logs
        self.converged = False
        #: Flag indicating solver completion in logs (if End is found)
        self.solve_completed = False
        #: Flag indicating whether the solver failed
        self.failed = False
        #: Timestep when the steady state solver converged
        self.converged_time = -1

        #: Flag indicating one timestep
        self._tick = False

        #: Flag indicating user exit (Ctrl+C) in watch mode
        self._user_exit = False

    def __call__(self):
        """Process log file"""
        pat_builtin = [grep(*x) for x in self._init_builtins()]
        patterns = pat_builtin + self._user_rules
        self._process_file(patterns)
        if self.solve_completed:
            self._save_state()

    def watch_file(self, target=None, wait_time=0.1):
        """Process a log file for an in-progress run.

        This method takes one parameter, ``target``, a coroutine that is called
        at the end of every timestep. See
        :class:`~caelus.post.plots.LogWatcher` for an example of using target
        to plot residuals for monitoring the run.

        Args:
            target (coroutine): A consumer acting on the data
            wait_time (seconds): Wait time between checking the log file for
                                 updates
        """
        import time
        import signal

        def _signal_handler(*args):
            """Handle quit signal for plot watching"""
            self._user_exit = True

        signal.signal(signal.SIGINT, _signal_handler)
        pat_builtin = [grep(*x) for x in self._init_builtins()]
        patterns = pat_builtin + self._user_rules
        with open(self.logfile) as fh:
            while (not self.solve_completed) and (not self._user_exit):
                line = fh.readline()
                if not line:
                    time.sleep(wait_time)
                elif line.strip():
                    for pat in patterns:
                        pat.send(line)
                    if self._tick and target is not None:
                        target.send(self.solve_completed)
                        self._tick = False
        if self.solve_completed:
            self._save_state()
        return self._user_exit

    def add_rule(self, regexp, actions):
        """Add a user-defined rule for processing

        Args:
            regexp (str): A string that can be compiled into a regexp
            action (func): A coroutine that can consume matching patterns
        """
        act_list = actions if hasattr(actions, "append") else [actions]
        self._user_rules.append(
            grep(regexp, act_list))

    def extend_rule(self, line_type, actions):
        """Extend a pre-defined regexp with extra functions

        The default action for LogProcessor is to output processed lines into
        files. Additional actions on pre-defined lines (e.g., "time") can be
        hooked via this method.

        Args:
            line_type (str): Pre-defined line type
            actions (list): A list of coroutines that receive the matching lines
        """
        act_list = actions if hasattr(actions, "append") else [actions]
        if line_type not in self.expressions:
            raise RuntimeError("No pre-defined line type: %s"%line_type)
        self._extra_rules.setdefault(line_type, []).extend(act_list)

    def _init_builtins(self):
        """Helper function to initialize builtin patterns"""
        for k, rexp in self.expressions.items():
            func = getattr(self, "%s_processor"%k)()
            yield (rexp, [func] + self._extra_rules.get(k, []))

    def _process_file(self, patterns):
        """Helper function to process logs of a completed run"""
        with open(self.logfile) as fh:
            for line in fh:
                for pat in patterns:
                    pat.send(line)

    @property
    def current_state(self):
        """Return the current state of the logs processor"""
        curr_state = dict(
            logfile=os.path.basename(self.logfile),
            time=self.time,
            converged=self.converged,
            solve_completed=self.solve_completed,
            converged_time=self.converged_time,
            failed=self.failed,
            fields=list(self.res_files.keys()),
            bounding_fields=list(self.bound_files.keys()))
        return curr_state

    def _save_state(self, filename=".logs_state.json"):
        """Save state of the logs for future introspection"""
        curr_state = self.current_state
        with open(join(self.logs_dir, filename), 'w') as fh:
            json.dump(curr_state, fh)

    @coroutine
    def time_processor(self):
        """Processor for the Time line in log files"""
        while True:
            rexp = (yield)
            self.time = float(rexp.group(1))
            self.time_str = rexp.group(1)
            # Reset subIteration counters
            for k in self.subiter_map:
                self.subiter_map[k] = 0
            self._tick = False

    @coroutine
    def residual_processor(self):
        """Process a residual line and output data to the relevant file."""
        def get_file(field, solver):
            """Helper method to get the file handle for a field.

            On first invocation, it creates the file with headers. On
            subsequent invocations it just returns the relevant file handle.
            """
            if not field in self.res_files:
                fh = open(join(self.logs_dir, field+".dat"), 'w')
                fh.write("# Field: %s; Solver: %s\n"%(field, solver))
                fh.write("Time SubIteration InitialResidual FinalResidual NoIterations\n")
                self.res_files[field] = fh
            return self.res_files[field]
        # end get_file

        try:
            while True:
                rexp = (yield)
                solver = rexp.group(1)       # e.g., PCB, GAMG, etc.
                field = rexp.group(2)        # Ux, Uy, p, etc.

                icorr = self.subiter_map.get(field, 0) + 1
                self.subiter_map[field] = icorr
                fh = get_file(field, solver)
                fh.write(
                    self.time_str + "\t%d\t"%icorr +
                    "\t".join([rexp.group(i) for i in range(3, 6)]) + "\n")
        except GeneratorExit:
            for fh in self.res_files.values():
                if not fh.closed:
                    fh.close()

    @coroutine
    def bounding_processor(self):
        """Process the bounding lines"""
        def get_file(field):
            """Helper method to get the file handle for a field.

            On first invocation, it creates the file with headers. On
            subsequent invocations it just returns the relevant file handle.
            """
            if not field in self.bound_files:
                fh = open(join(self.logs_dir, "bounding_"+field+".dat"), 'w')
                fh.write("# Bounding Field: %s\n"%(field))
                fh.write("Time SubIteration Min Max Average\n")
                self.bound_files[field] = fh
            return self.bound_files[field]
        # end get_file

        try:
            while True:
                rexp = (yield)
                field = rexp.group(1)
                icorr = self.subiter_map.get(field, 0)
                fh = get_file(field)
                fh.write(
                    self.time_str + "\t%d\t"%icorr +
                    "\t".join(rexp.group(i) for i in range(2, 5)) + "\n")
        except GeneratorExit:
            for fh in self.bound_files.values():
                if not fh.closed:
                    fh.close()

    @coroutine
    def continuity_processor(self):
        """Process continuity error lines from log file"""
        with open(join(self.logs_dir, "continuity_errors.dat"), 'w') as fh:
            fh.write("Time SubIteration LocalError GlobalError CumulativeError\n")
            while True:
                rexp = (yield)
                icorr = self.subiter_map.get('continuity', 0) + 1
                self.subiter_map['continuity'] = icorr
                fh.write(
                    self.time_str + "\t%d\t"%icorr +
                    "\t".join(x for x in rexp.groups()) + "\n")

    @coroutine
    def exec_time_processor(self):
        """Process execution/clock time lines"""
        with open(join(self.logs_dir, "clock_time.dat"), 'w') as fh:
            fh.write("Time ExecutionTime ClockTime\n")
            while True:
                rexp = (yield)
                fh.write(self.time_str + "\t" +
                         "\t".join(x for x in rexp.groups()) + "\n")
                self._tick = True

    @coroutine
    def courant_processor(self):
        """Process Courant Number lines"""
        with open(join(self.logs_dir, "courant.dat"), 'w') as fh:
            fh.write("Time CoMean CoMax\n")
            while True:
                rexp = (yield)
                fh.write(self.time_str + "\t" +
                         "\t".join(x for x in rexp.groups()) + "\n")

    @coroutine
    def convergence_processor(self):
        """Process convergence information (steady solvers only)"""
        while True:
            rexp = (yield)
            self.converged = True
            self.converged_time = int(rexp.group(2))

    @coroutine
    def completion_processor(self):
        """Process End line indicating solver completion"""
        while True:
            _ = (yield)
            self.solve_completed = True

    @coroutine
    def exiting_processor(self):
        """Process exiting option"""
        while True:
            _ = (yield)
            self.failed = True
            self.converged = False
            self.solve_completed = False

    @coroutine
    def fatal_error_processor(self):
        """Process CAELUS FATAL ERROR line"""
        while True:
            _ = (yield)
            self.failed = True
            self.converged = False
            self.solve_completed = False

class SolverLog(object):
    """Caelus solver log file interface.

    :class:`SolverLog` extracts information from solver outputs and allows
    interaction with the log data as ``numpy.ndarray`` or ``pandas.Dataframe``
    objects.
    """

    def __init__(self, case_dir=None,
                 logs_dir="logs", force_reload=False,
                 logfile=None):
        """
        Args:
            case_dir (path): Absolute path to case directory
            logs_dir (path): Path to logs directory relative to case_dir

            force_reload (bool): If True, force reread of the log file even if
                                 the logs were processed previously.

            logfile (file): If force_reload, then log file to process

        Raises:
            RuntimeError: An error is raised if no logs directory is available
                and the user has not provided a logfile that can be processed
                on the fly during initialization.
        """
        self.casedir = case_dir or os.getcwd()
        self.logs_dir = os.path.join(self.casedir, logs_dir)
        has_logs = os.path.exists(
            os.path.join(self.logs_dir, ".logs_state.json"))

        data = {}
        if not has_logs and logfile is None:
            raise RuntimeError("Cannot find processed logs data. "
                               "Provide a valid log file.")
        elif has_logs:
            data = json.load(open(
                os.path.join(self.logs_dir, ".logs_state.json")))
            if logfile:
                inpfile = os.path.basename(logfile)
                oldfile = os.path.basename(data.get("logfile", None))
                if (oldfile is None) or (inpfile != oldfile):
                    force_reload = True

        self.solve_completed = False
        self.failed = False
        self.fields = []
        self.bounding_fields = []
        if force_reload or not has_logs:
            logs = LogProcessor(logfile,
                                self.casedir, logs_dir)
            logs()
            data = logs.current_state

        for key, val in data.items():
            setattr(self, key, val)
        if not self.solve_completed:
            _lgr.warning("Solve not completed in %s", self.casedir)
        if self.failed:
            _lgr.warning("Detected failed run in %s", self.casedir)

    def residual(self, field, all_cols=False):
        """Return the residual time-history for a field"""
        if field not in self.fields:
            raise KeyError("Invalid field name: %s. Valid fields are: %s"%
                           (field, self.fields))
        fname = os.path.join(self.logs_dir, field+".dat")
        data = np.loadtxt(fname, skiprows=2)
        return data if all_cols else data[:, :3]

    def bounding_var(self, field):
        """Return the bounding information for a field"""
        if field not in self.bounding_fields:
            raise KeyError("Invalid field name: %s. Valid fields are: %s"%
                           (field, self.bounding_fields))
        fname = os.path.join(self.logs_dir, "bounding_"+field+".dat")
        data = np.loadtxt(fname, skiprows=2)
        return data

    def continuity_errors(self):
        """Return the time history of continuity errors"""
        fname = os.path.join(self.logs_dir, "continuity_errors.dat")
        data = np.loadtxt(fname, skiprows=1)
        return data
