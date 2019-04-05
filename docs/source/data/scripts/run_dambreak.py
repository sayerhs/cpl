# -*- coding: utf-8 -*-

"""
Test low-level python execution interface

Works with tutorials/multiphase/vof/vofSolver/ras/damBreak
"""

import os
import sys
import shutil

import pandas as pd
import matplotlib.pyplot as plt

from caelus.config.cmlenv import cml_get_version
from caelus.io import DictFile
from caelus.run.cmd import CaelusCmd
from caelus.run.core import get_mpi_size
from caelus.post.logs import LogProcessor, SolverLog
from caelus.post.plots import CaelusPlot

print("Searching for default caelus version...")
cenv_default = cml_get_version()

cenv = cenv_default
print("Using Caelus version: " + cenv.version)
print("Caelus path: " + cenv.project_dir)

status = 0
print("Executing blockMesh... ")
caelus_cmd = CaelusCmd("blockMesh", cml_env=cenv)
status = caelus_cmd()
if status != 0:
    print("ERROR generating blockMesh. Exiting!")
    sys.exit(1)

shutil.copy2("0/alpha1.org", "0/alpha1")

status = 0
print("Executing funkySetFields... ")
caelus_cmd = CaelusCmd("funkySetFields", cml_env=cenv)
caelus_cmd.cml_exe_args = "-latestTime"
status = caelus_cmd()
if status != 0:
    print("ERROR running funkySetFields. Exiting!")
    sys.exit(1)

if os.path.isfile("system/decomposeParDict"):
    parallel = True
    decompDict = DictFile.load("system/decomposeParDict")
else:
    parallel = False

status = 0
vof_cmd = CaelusCmd("vofSolver", cml_env=cenv)

if parallel:
    print("Executing decomposePar... ")
    decomp_cmd = CaelusCmd("decomposePar", cml_env=cenv)
    status = decomp_cmd()
    if status != 0:
        print("ERROR running decomposePar. Exiting!")
        sys.exit(1)
    vof_cmd.num_mpi_ranks = decompDict['numberOfSubdomains']
    vof_cmd.parallel = True
    print("Executing vofSolver in parallel on %d cores..."%vof_cmd.num_mpi_ranks)

else:
    print("Executing vofSolver...")

status = vof_cmd()
if status != 0:
    print("ERROR running vofSolver. Exiting!")
    sys.exit(1)

print("Processing logs... ")
clog = SolverLog(logfile="vofSolver.log")
cplot = CaelusPlot(clog.casedir)
cplot.plot_continuity_errors = True
cplot.plot_residuals_hist(plotfile="residuals.png")

