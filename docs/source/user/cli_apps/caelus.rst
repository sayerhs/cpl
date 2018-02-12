.. _cli_apps_caelus:

``caelus`` -- Common CPL actions
================================

.. versionadded:: 0.0.2

.. program:: caelus

The `caelus` command provides various sub-commands that can be used to perform
common tasks using the CPL library. Currently the following sub-commands (or
actions) are available through the :program:`caelus` script.

=========== ==================================================================
Action      Purpose
=========== ==================================================================
``cfg``     Print CPL configuration to stdout or file
``env``     Generate an environment file for sourcing within bash or csh shell
``clone``   Clone a case directory
``tasks``   Automatic execution of workflow from a YAML file
``run``     Run a CML executable in the appropriate environment
``logs``    Parse a solver log file and extract data for analysis
``clean``   Clean a case directory after execution
=========== ==================================================================

.. note::

   The script also supports the :option:`common options <cpl -h>` documented in
   the previous section. Care must be take to include the common options before
   the subcommand, i.e.,

   .. code-block:: bash

      # Correct usage
      caelus -vvv cfg -f caelus.yaml

      # The following will generate an error
      # caelus cfg -vvv # ERROR

caelus cfg -- Print CPL configuration
-------------------------------------

Print out the configuration dictionary currently in use by CPL. This will be a
combination of all the options loaded from the configuration files described in
:ref:`configuration <configuration>` section. By default, the command prints
the YAML-formatted dictionary to the standard output. The output can be
redirected to a file by using the :option:`caelus cfg -f` option. This is useful
for debugging.

.. program:: caelus cfg

.. code-block:: bash

   $ caelus cfg -h
   usage: caelus cfg [-h] [-f CONFIG_FILE] [-b]

   Dump CPL configuration

   optional arguments:
     -h, --help            show this help message and exit
     -f CONFIG_FILE, --config-file CONFIG_FILE
                           Write to file instead of standard output
     -b, --no-backup       Overwrite existing config without saving a backup

.. option:: -f output_file, --config-file output_file

   Save the current CPL configuration to the ``output_file`` instead of printing
   to standard output.

.. option:: -b, --no-backup

   By default, when using the :option:`caelus cfg -f` CPL will create a backup
   of any existing configuration file before writing a new file. This option
   overrides the behavior and will not create backups of existing configurations
   before overwriting the file.

caelus clone -- Clone a case directory
--------------------------------------

.. program:: caelus clone

``caelus clone`` takes to mandatory parameters, the source template case
directory, and name of the new case that is created. By default, the new case
directory is created in the current working directory and must not already
exist. CPL will not attempt to overwrite existing directories during clone.

.. code-block:: bash

   $ caelus clone -h
   usage: caelus clone [-h] [-m] [-z] [-s] [-e EXTRA_PATTERNS] [-d BASE_DIR]
                       template_dir case_name

   Clone a case directory into a new folder.

   positional arguments:
     template_dir          Valid Caelus case directory to clone.
     case_name             Name of the new case directory.

   optional arguments:
     -h, --help            show this help message and exit
     -m, --skip-mesh       skip mesh directory while cloning
     -z, --skip-zero       skip 0 directory while cloning
     -s, --skip-scripts    skip scripts while cloning
     -e EXTRA_PATTERNS, --extra-patterns EXTRA_PATTERNS
                           shell wildcard patterns matching additional files to
                           ignore
     -d BASE_DIR, --base-dir BASE_DIR
                           directory where the new case directory is created


.. option:: -m, --skip-mesh

   Do not copy the :file:`constant/polyMesh` directory when cloning. The default
   behavior is to copy the mesh along with the case directory.

.. option:: -z, --skip-zero

   Do not copy the :file:`0` directory during clone. The default behavior copies
   time ``t=0`` directory.

.. option:: -s, --skip-scripts

   Do not copy any python or YAML scripts during clone.

.. option:: -e pattern, --extra-patterns pattern

   A shell-wildcard pattern used to skip additional files that might exist in
   the source directory that must be skipped while cloning the case directory.
   This option can be repeated multiple times to provide more than one pattern.

   .. code-block:: bash

      # Skip all bash files and text files in the source directory
      caelus clone -e "*.sh" -e "*.txt" old_case_dir new_case_dir

.. option:: -d basedir, --base-dir basedir

   By default, the new case directory is created in the current working
   directory. This option allows the user to modify the behavior and create the
   new case in a different location. Useful for use within scripts.
