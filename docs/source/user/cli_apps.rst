.. _cli_apps_user:

Command-line Applications
=========================

CPL provides command-line interface (CLI) to several frequently used workflows
without having to write custom python scripts to access features within the
library. These CLI apps are described in detail in the following sections.

Common CLI options
------------------

All CPL command-line applications support a few common options. These options
are described below:

.. program:: cpl

.. option:: -h, --help

   Print a brief help message that describes the purpose of the application and
   what options are available when interacting with the application.

.. option:: --version

   Print the CPL version number and exit. Useful for submitting bug-reports,
   etc.

.. option:: -v, --verbose

   Increase the verbosity of messages printed to the standard output. Use
   ``-vv`` and ``-vvv`` to progressively increase verbosity of output.

.. option:: --no-log

   Disable logging messages from the script to a log file.

.. option:: --cli-logs log_file

   Customize the filename used to capture log messages during execution. This
   overrides the configuration parameter :confval:`log_file
   <caelus.logging.log_file>` provided in the user configuration files.


Available command-line applications
-----------------------------------

.. toctree::
   :maxdepth: 3

   cli_apps/caelus
   cli_apps/caelus_tutorials
