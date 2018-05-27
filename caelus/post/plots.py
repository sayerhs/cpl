# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position

"""\
Caelus Plotting Utilities
-------------------------

This module provides the capability to plot various quantities of interest
using matplotlib through :class:`CaelusPlot`.
"""

import os
import logging
import warnings
from contextlib import contextmanager
from collections import OrderedDict

import six
import numpy as np
import matplotlib.pyplot as plt

from .logs import SolverLog
from ..utils import osutils
from ..utils import coroutines
from .logs import LogProcessor

_lgr = logging.getLogger(__name__)

@contextmanager
def mpl_settings(backend="agg"):
    """Temporarily switch matplotlib settings for a plot"""
    cur_backend = plt.get_backend()
    if cur_backend.lower() != backend.lower():
        plt.switch_backend(backend)
    yield
    plt.switch_backend(cur_backend)

def make_plot_method(func):
    """Make a wrapper plot method"""
    def plot_wrapper(self, plotfile=None, dpi=300, **kwargs):
        """%s

            plotfile: File to save plot (e.g., residuals.png)
            dpi: Resolution for saving plots (default=300)
        """
        if plotfile:
            osutils.ensure_directory(self.plotdir)
            with mpl_settings("agg"):
                out = func(self, **kwargs)
                if out is None:
                    return
                outfile = os.path.join(self.plotdir, plotfile)
                plt.savefig(outfile, dpi=dpi,
                            bbox_inches='tight')
                _lgr.info("Saved figure: %s", outfile)
                plt.close()
        else:
            return func(self, **kwargs)

    plot_wrapper.__doc__ = plot_wrapper.__doc__%func.__doc__
    return plot_wrapper

class PlotsMeta(type):
    """Provide interactive and non-interactive versions of plot methods.

    This metaclass automatically wraps methods starting with ``_plot`` such
    that these methods can be used in both interactive and non-interactive
    modes. Non-interactive modes are automatically enabled if the user provides
    a file name to save the resulting figure.
    """

    def __new__(mcls, name, bases, cdict):
        keys = list(cdict.keys())
        for key in keys:
            if key.startswith("_plot_"):
                cdict[key[1:]] = make_plot_method(cdict[key])
        cls = super(PlotsMeta, mcls).__new__(mcls, name, bases, cdict)
        return cls

@six.add_metaclass(PlotsMeta)
class CaelusPlot(object):
    """Caelus Data Plotting Interface

    Currently implemented:
        - Plot residual time history
        - Plot convergence of forces and force coeffcients
    """

    def __init__(self, casedir=None, plotdir="results"):
        """
        Args:
            casedir (path): Path to the case directory
            plotdir (path): Directory where figures are saved
        """
        #: Path to the case directory
        self.casedir = casedir or os.getcwd()
        #: Path to plots output directory
        self.plotdir = os.path.join(self.casedir, plotdir)

        #: Instance of :class:`~caelus.post.logs.SolverLog`
        self.solver_log = None

        #: Flag indicating whether continuity errors are plotted along with
        #: residuals
        self.plot_continuity_errors = False

    def _plot_residuals_hist(self, fields=None):
        """Plot time-history of residuals for a Caelus run

        Args:
            fields (list): Plot residuals only for the fields in this list
        """
        if self.solver_log is None:
            self.solver_log = SolverLog(self.casedir)
        logf = self.solver_log

        fig = plt.figure()
        ax = plt.subplot(111)
        ax.set_yscale('log')
        ax.set_xlabel('Time')
        ax.set_ylabel('Residuals')

        field_list = fields or logf.fields
        for field in field_list:
            res = logf.residual(field)
            # We only want initial residuals (iter = 1)
            idx = res[:, 1] == 1
            ax.plot(res[idx, 0], res[idx, 2], label=field)
        if self.plot_continuity_errors:
            cerrs = logf.continuity_errors()
            idx = cerrs[:, 1] == 1
            ax.plot(cerrs[idx, 0], np.abs(cerrs[idx, 2]), label="continuity")
        ax.grid(True)
        plt.legend()
        return (fig, ax)

    def _force_plot_helper(self,
                           func_object, filename,
                           ylabels):
        root = os.path.join(self.casedir, "postProcessing", func_object)
        times = os.listdir(root)
        if not times:
            _lgr.error("Cannot find '%s' data for plotting.", func_object)
            return None
        fpath = os.path.join(root, times[-1], filename)
        force_hist = np.loadtxt(fpath)
        # Extract time from the numpy array
        time = force_hist[:, 0]
        fig, axes = plt.subplots(nrows=3, ncols=1, sharex=True)
        for i, (ax, ylabel) in enumerate(zip(axes, ylabels)):
            ax.plot(time, force_hist[:, (3-i)])
            ax.set_ylabel(ylabel)
            ax.grid(True)
            if ax.is_last_row():
                ax.set_xlabel("Time")
        return (fig, axes)

    def _plot_force_coeffs_hist(self, func_object="forceCoeffs"):
        """Plot force coefficients

        Args:
            func_object (str): The function object used in controlDict
        """
        ylabels = ["$C_l$", "$C_d$", "$C_m$"]
        return self._force_plot_helper(
            func_object, "forceCoeffs.dat", ylabels)

    def _plot_forces_hist(self, func_object="forces"):
        """Plot forces

        Args:
            func_object (str): The function object used in controlDict
        """
        ylabels = ["Lift", "Drag", "Moment"]
        return self._force_plot_helper(
            func_object, "forces.dat", ylabels)

class LogWatcher(object):
    """Real-time log monitoring utility"""

    def __init__(self, logfile, case_dir=None):
        """
        Args:
            logfile (str): Name of the Caelus log file
            casedir (path): Path to the case directory (default: cwd)
        """
        self.logprocessor = LogProcessor(logfile, case_dir)
        # Flag indicating new data is available for plot updates
        self._needs_update = False
        #: List of fields to plot. If None, plots all available fields
        self.plot_fields = []
        #: List of fields to skip. If None, plots all available fields
        self.skip_fields = []
        #: Time array used for plotting data
        self.time_array = None
        #: Dictionary containing fields requested for plotting and data
        #: extracted from log file so far
        self._field_data = OrderedDict()
        # Flag for initialization
        self._need_init = True
        # Flag indicating whether continuity errors are plotted
        self.plot_continuity_errors = False

    def __call__(self):
        """Run the residual watcher"""
        # Register time and residual consumers with LogProcessor
        self.logprocessor.extend_rule(
            "time", self.time_processor())
        self.logprocessor.extend_rule(
            "residual", self.residual_processor())

        if self.plot_continuity_errors:
            self.logprocessor.extend_rule(
                "continuity", self.continuity_processor())
        with warnings.catch_warnings():
            # Quell warning issued by matplotlib during the first timestep for
            # axis limits
            warnings.simplefilter("ignore", UserWarning)
            print("Starting residuals monitor; Ctrl+C to quit...")
            user_exit = self.logprocessor.watch_file(self.plot_residuals())
            if self.logprocessor.solve_completed:
                six.moves.input("Run has completed. Hit <Enter> to quit: ")
            plt.close()
            return user_exit

    def skip_field(self, field):
        """Helper function to determine if field must be processed"""
        if field in self.skip_fields:
            return True
        elif not self.plot_fields:
            return False
        elif field in self.plot_fields:
            return False
        return True

    @coroutines.coroutine
    def time_processor(self):
        """Capture time array"""
        logp = self.logprocessor
        while True:
            _ = (yield)
            if self.time_array is None:
                self.time_array = np.array([logp.time])
            else:
                self.time_array = np.r_[self.time_array, logp.time]
            self._needs_update = False

    @coroutines.coroutine
    def residual_processor(self):
        """Capture residuals for plot updates"""
        logp = self.logprocessor
        while True:
            rexp = (yield)
            field = rexp.group(2)
            icorr = logp.subiter_map[field]
            if not self.skip_field(field) and icorr == 1:
                value = float(rexp.group(3))
                if field not in self._field_data:
                    self._field_data[field] = np.array([value])
                else:
                    data = self._field_data[field]
                    data = np.r_[data, value]
                    self._field_data[field] = data
                self._needs_update = True

    @coroutines.coroutine
    def continuity_processor(self):
        """Capture continuity errors for plot updates"""
        key = 'continuity'
        logp = self.logprocessor
        while True:
            rexp = (yield)
            icorr = logp.subiter_map[key]
            if icorr == 1:
                value = np.abs(float(rexp.group(1)))
                if key not in self._field_data:
                    self._field_data[key] = np.array([value])
                else:
                    data = self._field_data[key]
                    data = np.r_[data, value]
                    self._field_data[key] = data
                self._needs_update = True


    @coroutines.coroutine
    def plot_residuals(self):
        """Update plot for residuals"""
        logp = self.logprocessor
        self._need_init = True
        fig = plt.figure()
        ax = None # pylint: disable=invalid-name
        lines = {}
        fields = None
        title_str = "Case = %s; timestep = %%d"%(
            os.path.basename(logp.case_dir))
        tstep = 0
        while True:
            _ = (yield)
            tarr = self.time_array
            tstep += 1
            if not self._needs_update:
                continue
            if not self._need_init:
                for key, val in self._field_data.items():
                    line = lines[key]
                    line.set_data(tarr, val)
                ax.relim()
                ax.autoscale_view()
                plt.legend(fields)
                plt.title(title_str%tstep)
                fig.canvas.draw()
                fig.canvas.flush_events()
                plt.pause(0.00001)
            else:
                self._need_init = False
                plt.interactive(True)
                fields = self._field_data.keys()
                ax = plt.subplot(111)
                ax.set_yscale("log")
                ax.set_ylabel(r"$\log$(residual)")
                ax.set_xlabel("Time/Iterations")
                plt.grid()
                for key, val in self._field_data.items():
                    line, = ax.plot(tarr, val)
                    lines[key] = line
                plt.show()
                plt.pause(0.00001)
