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
from contextlib import contextmanager

import six
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

from .logs import SolverLog
from ..utils import osutils

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
    def plot_wrapper(self, plotfile=None, dpi=120, **kwargs):
        """%s

            plotfile: File to save plot (e.g., residuals.png)
            dpi: Resolution for saving plots (default=120)
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
            ax.grid(True)
            plt.legend(loc=3)
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
