.. _cli_apps_caelus_tutorials:

caelus_tutorials -- Run tutorials
=================================

.. program:: caelus_tutorials

This is a convenience command to automatically run tutorials provided within the
Caelus CML distribution.

::

   $ caelus_tutorials -h
   usage: caelus_tutorials [-h] [--version] [-v] [--no-log | --cli-logs CLI_LOGS]
                           [-d BASE_DIR] [-c CLONE_DIR] [-f TASK_FILE]
                           [-i INCLUDE_PATTERNS | -e EXCLUDE_PATTERNS]

   Run Caelus Tutorials

   optional arguments:
     -h, --help            show this help message and exit
     --version             show program's version number and exit
     -v, --verbose         increase verbosity of logging. Default: No
     --no-log              disable logging of script to file.
     --cli-logs CLI_LOGS   name of the log file (caelus_tutorials.log)
     -d BASE_DIR, --base-dir BASE_DIR
                           directory where tutorials are run
     -c CLONE_DIR, --clone-dir CLONE_DIR
                           copy tutorials from this directory
     --clean               clean tutorials from this directory
     -f TASK_FILE, --task-file TASK_FILE
                           task file containing tutorial actions
                           (run_tutorial.yaml)
     -i INCLUDE_PATTERNS, --include-patterns INCLUDE_PATTERNS
                           run tutorial case if it matches the shell wildcard
                           pattern
     -e EXCLUDE_PATTERNS, --exclude-patterns EXCLUDE_PATTERNS
                           exclude tutorials that match the shell wildcard
                           pattern

   Caelus Python Library (CPL) v0.0.2

.. option:: -f task_file, --task-file task_file

   The name of the task file used to execute the steps necessary to complete a
   tutorial. The default value is ``run_tutorial.yaml``

.. option:: -i pattern, --include-patterns pattern

   A shell wildcard pattern to match tutorial names that must be executed. This
   option can be used multiple times to match different patterns. For example,

   .. code-block:: console

      # Run all simpleSolver cases and pisoSolver's cavity case
      caelus_tutorials -i "*simpleSolver* -i "*cavity*"

   This option is mutually exclusive to :option:`caelus_tutorials -e`

.. option:: -e pattern, --exclude-patterns pattern

   A shell wildcard pattern to match tutorial names that are skipped during the
   tutorial run. This option can be used multiple times to match different
   patterns. For example,

   .. code-block:: console

      # Skip motorBikeSS and motorBikeLES cases
      caelus_tutorials -e "*motorBike*"

   This option is mutually exclusive to :option:`caelus_tutorials -i`
