.. _cli_apps_caelus_sim:

``caelus_sim`` -- Parametric Run CLI
====================================

.. versionadded: 0.2.0

.. program:: caelus_sim

The ``caelus_sim`` is a shell executable that provides a command-line interface
to setup and execute a parametric analysis. Currently, the following
sub-commands are available through :program:`caelus_sim` executable.

============ =========================================================
Action       Purpose
============ =========================================================
``setup``    Setup a new parametric run
``prep``     Execute pre-processing actions
``solve``    Run the solver
``post``     Execute post-processing actions
``status``   Print out status of the analysis
============ =========================================================

.. note::

   The script also supports :option:`common options <cpl -h>` documented
   previously. Care must be taken to include the common options before the
   subcommand, i.e.,

   .. code-block:: bash

      # Correct usage
      caelus_sim -v setup

      # Incorrect usage, will generate an error
      caelus_sim setup -v

caelus_sim setup -- Setup a parametric run
------------------------------------------

By default, this command will parse the :file:`caelus_sim.yaml` input file and
setup a new analysis under a new directory ``name`` provided either at the
command line or in the input file. The individual cases corresponding to the run
matrix appear as subdirectories to the top-level analysis directory.

.. program:: caelus_sim setup

.. code-block:: bash

   $ caelus_sim setup -h
   usage: caelus_sim setup [-h] [-n SIM_NAME] [-d BASE_DIR] [-s] [-p]
                           [-f SIM_CONFIG]

   setup a parametric run

   optional arguments:
     -h, --help            show this help message and exit
     -n SIM_NAME, --sim-name SIM_NAME
                           name of this simulation group
     -d BASE_DIR, --base-dir BASE_DIR
                           base directory where the simulation structure is
                           created
     -s, --submit          submit solve jobs on successful setup
     -p, --prep            run pre-processing steps after successful setup
     -f SIM_CONFIG, --sim-config SIM_CONFIG
                           YAML-formatted simulation configuration
                           (caelus_sim.yaml)

.. option:: -f, --sim-config

   The input file containing the details of the analysis to be performed.
   Default value is :file:`caelus_sim.yaml`

.. option:: -n, --sim-name

   Name of this parametric run. This option overrides the ``sim_name`` entry in
   the input file.

.. option:: -d, --base-dir

   Directory where the parametric analysis is setup. This directory must exist.
   Default value is the current working directory.

.. option:: -s, --submit

   Submit the solve jobs after setup is complete.

.. option:: -p, --prep

   Run pre-processing tasks upon successful setup.


caelus status -- Print status of the parametric runs
----------------------------------------------------

This command prints out the status of the runs so far.
