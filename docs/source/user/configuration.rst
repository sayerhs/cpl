.. _configuration:

Configuring Caelus Python Library
=================================

CPL provides a YAML-based configuration utility that can be used to customize
the library depending on the operating system and user's specific needs. A good
example is to provide non-standard install locations for the Caelus CML
executables, as well as using different versions of CML with CPL simultaneously.

The use of configuration file is optional, CPL provides defaults that should
work on most systems and will attempt to auto-detect CML installations on
standard paths. On Linux/OS X systems, CPL will look at
:file:`~/Caelus/caelus-VERSION` to determine the installed CML versions and use
the ``VERSION`` tag to determine the latest version to use. On Window systems,
the default search path is :file:`C:\\Caelus`.

Upon invocation, CPL will search and load configuration files from the following
locations, if available. The files are loaded in sequence shown below and
options found in succeeding files will overwrite configuration options found in
preceeding files.

#. Default configuration supplied with CPL;

#. The system-wide configuration in file pointed by environment variable
   :envvar:`CAELUSRC_SYSTEM` if it exists;

#. The per-user configuration file, if available. On Linux/OS X, this is the
   file :file:`~/.caelus.yaml`, and :file:`%APPDATA%/caelus.yaml` on Windows
   systems;

#. The per-user configuration file pointed by the environment variable
   :envvar:`CAELUSRC` if it exists;

#. The file ``caelus.yaml`` in the current working directory, if it exists.

While CPL provides a way to auto-discovered installed CML versions, often it
will be necessary to provide at least a system-wide or per-user configuration
file to allow CPL to use the right CML executables present in your system. A
sample CPL configuration is shown below :download:`download caelus.yaml
<../data/caelus_config.yaml>`:

.. literalinclude:: ../data/caelus_config.yaml
   :language: yaml

The above configuration would be suitable as as a system-wide or per-user
configuration stored in the home directory, and the user can override specific
options used for particular runs by using, for example, the following
:file:`caelus.yaml` within the case directory:

.. code-block:: yaml

   # Local CPL settings for this working directory
   caelus:
     logging:
       log_file: cpl_dev.log  # Change log file to a local file

     caelus_cml:
       default: "dev-gcc"     # Use the latest dev version for this run


Note that only options that are being overridden need to be specified. Other
options are populated from the system-wide or per-user configuration file if
they exist.

CPL Configuration Reference
---------------------------

CPL configuration files are in YAML format and must contain at least one node
:confval:`caelus`. Two other optional nodes can be present in the file,
:confval:`caelus_scripts` and :confval:`caelus_user` whose purpose is described
below.

.. confval:: caelus

   The root YAML node containing the core CPL configuration object. This node
   contains all configuration options used internally by the library.

.. confval:: caelus_scripts

   An optional node used to store configuration for CPL CLI apps.

.. confval:: caelus_user

   An optional node node reserved for user scripts and applications that will be
   built upon CPL.

.. note::

   In the following sections, the configuration parameters are documented in the
   format ``root_note.sub_node.config_parameter``. Please see the sample
   configuration file above for the exact nesting structure used for
   :confval:`caelus.logging.log_file`.

Core library configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. confval:: caelus.logging

   This section of the configuration file controls the logging options for the
   CPL library. By default, CPL only outputs messages to the standard output.
   Users can optionally save all messages from CPL into a log file of their
   choice. This is useful for tracking and troubleshooting, or providing
   additional information regarding bugs observed by the user.

   Internally, CPL uses the :pythonlib:`logging` module. For brevity, messages
   output to console are usually at log levels ``INFO`` or higher. However,
   all messages ``DEBUG`` and above are captured in log files.

.. confval:: caelus.logging.log_to_file

   A Boolean value indicating whether CPL should output messages to the log
   file. The default value is ``false``. If set to ``true``, then the log
   messages will also be saved to the file indicated by :confval:`log_file
   <caelus.logging.log_file>` as well as output to the console.

.. confval:: caelus.logging.log_file

   Filename where the log messages are saved if :confval:`log_to_file
   <caelus.logging.log_to_file>` evaluates to ``True``.

CML version configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. confval:: caelus.caelus_cml

   The primary purpose of CPL is to interact with CML executables and utilities.
   This section informs CPL of the various CML installations available on a
   system and the desired *version* used by CPL when invoking CML executables.

.. confval:: caelus.caelus_cml.default

   A string parameter indicating default version used when invoking CML
   executables. It must be one of the :confval:`version
   <caelus.caelus_cml.versions.version>` entries provided in the file.
   Alternately, the user can specify ``latest`` to indicate that the latest
   version must be used. If users rely on auto-discovery of Caelus versions in
   default install locations, then it is recommended that this value be
   ``latest`` so that CPL picks the latest CML version. For example, with the
   following configuration, CPL will choose version ``7.04`` when attempting to
   execute programs like ``pisoSolver``.

   .. code-block:: yaml

      caelus:
        caelus_cml:
          default: "latest"

          versions:
            - version: "6.10"
              path: ~/Caelus/caelus-6.10

            - version: "7.04"
              path: ~/Caelus/caelus-7.04

.. confval:: caelus.caelus_cml.versions

   A list of configuration mapping listing various versions available for use
   with CPL. It is recommended that the users only provide :confval:`version
   <caelus.caelus_cml.versions.version>` and :confval:`path
   <caelus.caelus_cml.versions.path>` entries, the remaining entries are
   optional. CPL will auto-detect remaining parmeters.

.. confval:: caelus.caelus_cml.versions.version

   A unique string identifier that is used to tag this specific instance of CML
   installation. Typically, this is the version number of the Caelus CML
   release, e.g., ``7.04``. However, as indicated in the example CPL
   configuration file, users can use any unique tag to identify a specific
   version. If is identifier does not follow the conventional version number
   format, then it is recommended that the user provide a specific version in
   :confval:`caelus.caelus_cml.default` instead of using ``latest``.

.. confval:: caelus.caelus_cml.versions.path

   The path to the Caelus install. This is equivalent to the directory pointed
   by the :envvar:`CAELUS_PROJECT_DIR` environment variable, e.g.,
   :file:`/home/caelus_user/projects/caelus/caelus-7.04`.

.. confval:: caelus.caelus_cml.versions.build_option

   A string parameter identifying the Caelus build, if multiple builds are
   present within a CML install, to be used with CPL. This is an **expert** only
   option used by developers who are testing multiple compilers and build
   options. It is recommended that the normal users let CPL autodetect the build
   option.

.. confval:: caelus.caelus_cml.versions.mpi_root

   Path to the MPI installation used to compile Caelus for parallel execution.
   By default, CPL expects the MPI library to be present within the project
   directory.

.. confval:: caelus.caelus_cml.versions.mpi_bin_path

   Directory containing MPI binaries used for :program:`mpiexec` when executing
   in parallel mode. If absent, CPL will assume that the binaries are located
   within the subdirectory :file:`bin` in the path pointed by :confval:`mpi_root
   <caelus.caelus_cml.versions.mpi_root>`.

.. confval:: caelus.caelus_cml.versions.mpi_lib_path

   Directory containing MPI libraries used for :program:`mpiexec` when executing
   in parallel mode. If absent, CPL will assume that the libraries are located
   within the subdirectory :file:`lib` in the path pointed by :confval:`mpi_root
   <caelus.caelus_cml.versions.mpi_root>`.
