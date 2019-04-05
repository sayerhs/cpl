.. _tuts_cpl_script:

Custom scripts using CPL
=========================

CPL can be used to create custome CFD workflows that may fall outside the
capabilities of the command-line applications. The classes used to build
the command-line applications can likewise be use to create custom Python
scripts, as shown with following example.

This tutorial mimics the workflow of the task file used for the VOF
mutliphase solver `damBreak` tutorial provided with Caelus. To follow along
it is recommended that the user download the
:download:`custom CPL script <../../data/scripts/run_dambreak.py>`. It is
assumed the user is executing the script from within the
:file:`$CAELUS_PROJECT_DIR/tutorials/multiphase/vof/vofSolver/ras/damBreak`
directory. To use CPL's Python interface directly, the user needs to ensure
is CPL installed, preferably in a conda or virtualenv environment (see:
:ref:`installation`). As a Python script, other non-CPL functionality can
be used in coordination with CPL (e.g. `matplotlib`).

.. code-block:: python

    import os
    import sys
    import shutil

    import matplotlib.pyplot as plt

Several CPL classes and methods are required. Refer to the CPL Python API
docs (:mod:`caelus`) for a complete listing of modules and associated
functionality.

.. code-block:: python

    from caelus.config.cmlenv import cml_get_version
    from caelus.run.cmd import CaelusCmd
    from caelus.run.core import get_mpi_size
    from caelus.post.logs import LogProcessor, SolverLog
    from caelus.post.plots import CaelusPlot

An environment specifies the particular CML version and installation
location. This examples loads the default (no argument to
:class:`~caelus.config.cmlenv.cml_get_version` returns the default).

.. code-block:: python

    print("Searching for default caelus version...")
    cenv_default = cml_get_version()

    cenv = cenv_default
    print("Using Caelus version: " + cenv.version)
    print("Caelus path: " + cenv.project_dir)

Commands are run using :class:`~caelus.run.cmd.CaelusCmd`. The 
environment to the job manager object. The command is executed by
calling the object and a boolean is returned to enable status checking.
Here, the meshing application, `blockMesh`, is run.

.. code-block:: python

    status = 0
    print("Executing blockMesh... ")
    caelus_cmd = CaelusCmd("blockMesh", cml_env=cenv)
    status = caelus_cmd()
    if status != 0:
        print("ERROR generating blockMesh. Exiting!")
        sys.exit(1)

Use built-in Python modules for filesystem related tasks.

.. code-block:: python

    shutil.copy2("0/alpha1.org", "0/alpha1")

The solution is initialized solution using `funkySetFields` with
the :class:`~caelus.run.cmd.CaelusCmd` as shown previously.

.. code-block:: python

    status = 0
    print("Executing funkySetFields... ")
    caelus_cmd = CaelusCmd("funkySetFields", cml_env=cenv)
    caelus_cmd.cml_exe_args = "-latestTime"
    status = caelus_cmd()
    if status != 0:
        print("ERROR running funkySetFields. Exiting!")
        sys.exit(1)

An automated way to detect and set up a parallel run is to check for a
:file:`system/decomposeParDict` file, use the
:class:`~caelus.io.caelusdict.CaelusDict` class to retrieve the 
`numberOfSubdomains` parameter, and set the number of MPI ranks
to run applications with.

.. code-block:: python

    if os.path.isfile("system/decomposeParDict"):
        parallel = True
        decompDict = DictFile.load("system/decomposeParDict")
    else:
        parallel = False

    status = 0
    solver_cmd = CaelusCmd("vofSolver", cml_env=cenv)

    if parallel:
        print("Executing decomposePar... ")
        decomp_cmd = CaelusCmd("decomposePar", cml_env=cenv)
        status = decomp_cmd()
        if status != 0:
            print("ERROR running decomposePar. Exiting!")
            sys.exit(1)
        solver_cmd.num_mpi_ranks = decompDict['numberOfSubdomains']
        solver_cmd.parallel = True
        print("Executing vofSolver in parallel on %d cores..."%solver_cmd.num_mpi_ranks)

    else:
        print("Executing vofSolver...")

    status = solver_cmd()
    if status != 0:
        print("ERROR running vofSolver. Exiting!")
        sys.exit(1)

Finally, the :class:`~caelus.post.logs.SolverLog` class is invoked to parse the log file
and generate a plot of the residuals.

.. code-block:: python

    print("Processing logs... ")
    clog = SolverLog(logfile="vofSolver.log")
    cplot = CaelusPlot(clog.casedir)
    cplot.plot_continuity_errors = True
    cplot.plot_residuals_hist(plotfile="residuals.png")

