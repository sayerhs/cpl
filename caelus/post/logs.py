# -*- coding: utf-8 -*-

"""\
Caelus Log Analyzer
-------------------
"""

import os
from os.path import join
from collections import OrderedDict
from ..utils import osutils
from ..utils.coroutines import coroutine, grep

class LogProcessor(object):
    """Process the log file and extract information for analysis.

    """

    #: Regular expressions that most common lines of interest within a log file
    expressions = dict(
        time=r"^Time = (\S+)",
        courant=r"^Courant Number mean: (\S+) max: (\S+)",
        residual=r"(\S+): *Solving for (\S+), Initial residual = (\S+), Final residual = (\S+), No Iterations (\S+)",
        continuity=r"time step continuity errors : sum local = (\S+), global = (\S+), cumulative = (\S+)",
        exec_time=r"ExecutionTime = (\S+) s  ClockTime = (\S+) s",
        convergence=r"(\S+) solution converged in (\S+) iterations",
        completion=r"^End$",
    )

    #: Format for outputs of residuals
    res_fmt = "%15.5f %5d %15.6e %15.6e %5d\n"

    #: Format for output of continuity errors
    cont_err_fmt = "%15.5f %5d %15.6e %15.6e %15.6e\n"

    #: Execution/clock time formatter
    exec_time_fmt = "%15.5f %15.5f %15.5f\n"

    #: Courant number formatter
    courant_fmt = "%15.5f %15.5e %15.5e\n"

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
        #: (variable, corrector) pairs tracking the number of predictor
        #: correctors for each flow variable
        self.corrs = {}

        #: Open file handles for the residual outputs
        self.file_handles = OrderedDict()

        #: Flag indicating convergence message in logs
        self.converged = False
        #: Flag indicating solver completion in logs (if End is found)
        self.solve_completed = False
        #: Timestep when the steady state solver converged
        self.converged_time = -1

    def __call__(self, watch=False):
        """Process log file"""
        patterns = [grep(*x) for x in self._init_builtins()]
        if watch:
            self._watch_file(patterns)
        else:
            self._process_file(patterns)

    def _init_builtins(self):
        """Helper function to initialize builtin patterns"""
        for k, rexp in self.expressions.items():
            func = getattr(self, "%s_processor"%k)()
            yield (rexp, [func])

    def _process_file(self, patterns):
        """Helper function to process logs of a completed run"""
        with open(self.logfile) as fh:
            for line in fh:
                for pat in patterns:
                    pat.send(line)

    def _watch_file(self, patterns):
        """Helper function to process logs of a completed run"""


    @coroutine
    def time_processor(self):
        """Processor for the Time line in log files"""
        while True:
            rexp = (yield)
            self.time = float(rexp.group(1))
            # Reset corrector counters
            for k in self.corrs:
                self.corrs[k] = 0

    @coroutine
    def residual_processor(self):
        """Process a residual line and output data to the relevant file."""
        def get_file(field, solver):
            """Helper method to get the file handle for a field.

            On first invocation, it creates the file with headers. On
            subsequent invocations it just returns the relevant file handle.
            """
            if not field in self.file_handles:
                fh = open(join(self.logs_dir, field+".dat"), 'w')
                fh.write("# Field: %s; Solver: %s\n"%(field, solver))
                fh.write("Time Corrector InitialResidual FinalResidual NoIterations\n")
                self.file_handles[field] = fh
            return self.file_handles[field]
        # end get_file

        try:
            while True:
                rexp = (yield)
                solver = rexp.group(1)       # e.g., PCB, GAMG, etc.
                field = rexp.group(2)        # Ux, Uy, p, etc.
                ires = float(rexp.group(3))  # Initial residual
                fres = float(rexp.group(4))  # Final residual
                iters = int(rexp.group(5))   # No Iterations

                icorr = self.corrs.get(field, 0) + 1
                self.corrs[field] = icorr
                fh = get_file(field, solver)
                fh.write(self.res_fmt%(
                    self.time, icorr, ires, fres, iters))
        except GeneratorExit:
            for fh in self.file_handles.values():
                fh.close()

    @coroutine
    def continuity_processor(self):
        """Process continuity error lines from log file"""
        with open(join(self.logs_dir, "continuity_errors.dat"), 'w') as fh:
            fh.write("Time Corrector LocalError GlobalError CumulativeError\n")
            while True:
                rexp = (yield)
                lce, gce, cce = [float(x) for x in rexp.groups()]
                icorr = self.corrs.get('continuity', 0) + 1
                self.corrs['continuity'] = icorr
                fh.write(self.cont_err_fmt%(
                    self.time, icorr, lce, gce, cce))

    @coroutine
    def exec_time_processor(self):
        """Process execution/clock time lines"""
        with open(join(self.logs_dir, "clock_time.dat"), 'w') as fh:
            fh.write("Time ExecutionTime ClockTime\n")
            while True:
                rexp = (yield)
                etime, ctime = [float(x) for x in rexp.groups()]
                fh.write(self.exec_time_fmt%(
                    self.time, etime, ctime))

    @coroutine
    def courant_processor(self):
        """Process Courant Number lines"""
        with open(join(self.logs_dir, "courant.dat"), 'w') as fh:
            fh.write("Time CoMean CoMax\n")
            while True:
                rexp = (yield)
                cmean, cmax = [float(x) for x in rexp.groups()]
                fh.write(self.courant_fmt%(
                    self.time, cmean, cmax))

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
