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

caelus env -- write shell environment file
------------------------------------------

Write a shell environment file to be sourced/called by the platform specific
shell. This will be a combination of all the options loaded from the
configuration files described in :ref:`configuration <configuration>` section. 
The output can be redirected to a directory by using the :option:`caelus env -d` option.
This is useful for legacy workflows.

.. program:: caelus env

.. code-block:: bash

   $ caelus env -h
   usage: caelus env [-h] [-d WRITE_DIR]

   Write environment variables that can be sourced into the SHELL environment

   optional arguments:
     -h, --help            show this help message and exit
     -d WRITE_DIR, --write-dir WRITE_DIR
                           Path where the environment files are written

.. option:: -d write_dir, --write_dir write_dir

    Save the environment file to the ``write_dir`` instead of the current working
    directory

caelus clone -- Clone a case directory
--------------------------------------

.. program:: caelus clone

``caelus clone`` takes two mandatory parameters, the source template case
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

.. _cli_apps_caelus_tasks:

caelus tasks -- run tasks from a file
-------------------------------------

Read and execute tasks from a YAML-formatted file. Task files could be considered
recipes or workflows. By default, it reads ``caelus_tasks.yaml`` from the current
directory. The behavior can be modified to read other file names and locations.

.. program:: caelus tasks

.. code-block:: bash

   $ caelus tasks -h
   usage: caelus tasks [-h] [-f FILE]

   Run pre-defined tasks within a case directory read from a YAML-formatted file.

   optional arguments:
     -h, --help            show this help message and exit
     -f FILE, --file FILE  file containing tasks to execute (caelus_tasks.yaml)

.. option:: -f task_file, --file task_file

   Execute the task file named ``task_file`` instead of caelus_tasks.yaml in current
   working directory

caelus run -- run a Caelus executable in the appropriate environment
--------------------------------------------------------------------

Run a single Caelus application. The application name is the one mandatory argument.
Additional command arguments can be specified. The behavior can be modified to enble
parallel execution of the application. By default, the application runs from the
current directory. This behavior can be modified to specify the case directory. Note:
when passing ``cmd_args``, ``--`` is required between ``run`` and ``cmd_name`` so the
cmd_args are parsed correctly. E.g. ``caelus run -- renumberMesh "-overwrite"``

.. program:: caelus run

.. code-block:: bash

   $ caelus run -h
   usage: caelus run [-h] [-p] [-l LOG_FILE] [-d CASE_DIR]
                  cmd_name [cmd_args [cmd_args ...]]

   Run a Caelus executable in the correct environment

   positional arguments:
     cmd_name              name of the Caelus executable
     cmd_args              additional arguments passed to command

   optional arguments:
     -h, --help            show this help message and exit
     -p, --parallel        run in parallel
     -l LOG_FILE, --log-file LOG_FILE
                           filename to redirect command output
     -d CASE_DIR, --case-dir CASE_DIR
                           path to the case directory

.. option:: -p, --parallel

   Run the executable in parallel

.. option:: -l log_file, --log-file log_file

   By default, a log file named ``<application>.log`` is created. This option allows
   the user to modify the behavior and create a differently named log file.

.. option:: -d casedir, --case-dir casedir

   By default, executables run from the current working directory. This option
   allows the user to modify the behavior and specify the path to the case
   directory.

caelus logs -- process a Caelus solver log file from a run
----------------------------------------------------------

Process a single Caelus solver log. The log file name is the one mandatory
argument. Additional command arguments can be specified. By default, the log
file is found in the current directory and the output is written to ``logs``
directory. The behavior can be modified to specify the case directory and output
directory.

.. program:: caelus logs

.. code-block:: bash

   $ caelus logs -h
   usage: caelus logs [-h] [-l LOGS_DIR] [-d CASE_DIR] [-p] [-f PLOT_FILE] [-w]
                  [-i INCLUDE_FIELDS | -e EXCLUDE_FIELDS]
                  log_file

   Process logfiles for a Caelus run

   positional arguments:
   log_file               log file (e.g., simpleSolver.log)

   optional arguments:
   -h, --help             show this help message and exit
   -l LOGS_DIR, --logs-dir LOGS_DIR
                          directory where logs are output (default: logs)
   -d CASE_DIR, --case-dir CASE_DIR
                          path to the case directory
   -p, --plot-residuals   generate residual time-history plots
   -f PLOT_FILE, --plot-file PLOT_FILE
                          file where plot is saved
   -w, --watch            Monitor residuals during a run
   -i INCLUDE_FIELDS, --include-fields INCLUDE_FIELDS
                          plot residuals for given fields
   -e EXCLUDE_FIELDS, --exclude-fields EXCLUDE_FIELDS

.. option:: -l logs_dir, --logs-dir logs_dir

   By default, the log files are output to ``logs``. This option allows
   the user to modify the behavior and create a differently named log file
   output directory.

.. option:: -d, case_dir, --case-dir case_dir

   By default, the log file is found in the current working directory. This
   option allows the user to specify the path to the case directory where the
   log file exists.

.. option:: -p, --plot-residuals

   This option allows the user to plot and save the residuals to an image file.

.. option:: -f plot_file, --plot-file plot_file

   By default, plots are saved to ``residuals.png`` in the current
   working directory. This option allows the user to modify the behavior
   and specify a differently named plot file.

.. option:: -w, --watch

   This option allows the user to dynamically monitor residuals for a log file
   from a currently run.

.. option:: -i include_fields, --include-fields include_fields

   By default, all field equation residuals are plotted. This option can be
   used to only include specific fields in residual plot. Multiple fields
   can be provided to this option. For example,

   .. code-block:: bash

      # Plot pressure and momentum residuals from simpleSolver case log
      caelus logs -p -i "p Ux Uy Uz" simpleSolver.log

.. option:: -e exclude_fields, --exclude-patterns exclude fields

   By default, all field equation residuals are plotted. This option can be
   used to exclude specific fields in residual plot. Multiple fields
   be provided to this option. For example,

   .. code-block:: bash

      # Exclude TKE and omega residuals from simpleSolver case log
      caelus logs -p -e "k epsilon" simpleSolver.log

caelus clean -- clean a Caelus case directory
---------------------------------------------

Cleans files generated by a run. By default, this function will always
preserve ``system``, ``constant``, and ``0`` directories as well as any
YAML or python files. The behavior can be modified to presevere
additional files and directories.

.. program:: caelus clean

.. code-block:: bash

   $ caelus clean -h
   usage: caelus clean [-h] [-d CASE_DIR] [-m] [-z] [-p PRESERVE]

   Clean a case directory

   optional arguments:
       -h, --help         show this help message and exit
       -d CASE_DIR, --case-dir CASE_DIR
                          path to the case directory
       -m, --clean-mesh   remove polyMesh directory
       -z, --clean-zero   remove 0 directory
       -p PRESERVE, --preserve PRESERVE
                          shell wildcard patterns of extra files to preserve

.. option:: -d, case_dir, --case-dir case_dir

   By default, the case directory is the current working directory. This
   option allows the user to specify the path to the case directory.

.. option:: -m, --clean-mesh

   By default, the ``polyMesh`` directory is not removed. This option allows
   the user to modify the behavior and remove the ``polyMesh`` directory.

.. option:: -z, --clean-zero

   By default, the ``0`` files are not cleaned. This option allows
   the user to modify the behavior and remove the ``0`` directory.

.. option:: -p preserve_pattern, --preserve preserve_pattern

   A shell-wildcard patterns of files or directories that will not
   be cleaned.
