.. _user_caelus_tasks:

Caelus Tasks
============

CPL provides a *tasks* interface to automate various aspects of the CFD
simulation workflow that can be executed by calling :program:`caelus tasks` (see
:ref:`tasks documentation <cli_apps_caelus_tasks>`).

Quick tutorial
---------------

The *tasks* interface requires a list of tasks provided in a YAML-formatted file
as shown below (:download:`download <../data/caelus_tasks.yaml>`):

.. literalinclude:: ../data/caelus_tasks.yaml
   :language: yaml

The file lists a set of actions to be executed sequentially by :program:`caelus
tasks`. The tasks can accept various options that can be used to further
customize the workflow. A sample interaction is shown below

::

   $ caelus -v tasks -f caelus_tasks.yaml
   INFO: Caelus Python Library (CPL) v0.1.0
   INFO: Caelus CML version: 7.04
   INFO: Loaded tasks from: cavity/caelus_tasks.yaml
   INFO: Begin executing tasks in cavity
   INFO: Cleaning case directory: cavity
   INFO: Executing command: blockMesh
   INFO: Executing command: pisoSolver
   INFO: Processing log file: pisoSolver.log
   INFO: Saved figure: cavity/residuals.pdf
   INFO: Residual time history saved to residuals.pdf
   INFO: Successfully executed 4 tasks in cavity
   INFO: All tasks executed successfully.

For a comprehensive list of task file examples, please consult the
:file:`run_tutorial.yaml` files in the :file:`tutorials` directory of Caelus CML
distribution. In particular, the
:file:`tutorials/incompressible/pimpleSolver/les/motorBike` case provides an
example of a tasks workflow involving two different case directories.

Tasks reference
---------------

This section documents the various *tasks* available currently within CPL and
the options that can be used to customize execution of those tasks.

- The task file must be in YAML format, and must contain one entry ``tasks``
  that is a list of tasks to be executed.

- The tasks are executed sequentially in the order provided until an error is
  encountered or all tasks are executed successfully.

- The tasks must be invoked from within a valid Caelus case directory (see
  ``task_set`` for an exception). All filenames in the task file are interpreted
  relative to the execution directory where the command is invoked.


run_command -- Run CML executables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This *task type* is used to execute a Caelus CML executable (e.g.,
:program:`blockMesh` or :program:`pimpleSolver`). CPL will ensure that the
appropriate version of CML is selected and the runtime enviornment is setup
properly prior to executing the task. The task must provide one mandatory
parameter :taskopt:`run_command.cmd_name` that is the name of the CML
executable. Several other options are available and are documented below. Example:

.. code-block:: yaml

   - run_command:
       cmd_name: potentialSolver
       cmd_args: "-initialiseUBCs -noFunctionObjects"
       parallel: true

.. taskopt:: run_command.cmd_name

   The name of the CML executable. This option is mandatory.

.. taskopt:: run_command.cmd_args

   Extra arguments that must be passed to the CML executable. It is recommended
   that arguments be enclosed in a double-quoted string. Default value is an
   empty string.

.. taskopt:: run_command.log_file

   The filename where the output of the command is redirected. By default, it is
   the CML executable name with the ``.log`` extension appended to it. The user
   can change this to any valid filename of their choice using this option.


.. taskopt:: run_command.parallel

   A Boolean flag indicating whether the executable is to be run in parallel
   mode. The default value is ``False``. If ``parallel`` is True, then the
   default options for job scheduler are used from CPL configuration file, but
   can be overriden with additional options to ``run_command``.

.. taskopt:: run_command.num_ranks

   The number of MPI ranks for a parallel run.

.. taskopt:: run_command.mpi_extra_args

   Extra arguments to be passed to :program:`mpiexec` command (e.g.,
   ``hostfile`` options). As with :taskopt:`cmd_args <run_command.cmd_args>`,
   enclose the options within quotes.

copy_files -- Copy files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This task copies files in a platform-agnostic manner.

.. taskopt:: copy_files.src

   A unix-style file pattern that is used to match the pattern of files to be
   copied. The path to the files must be relative to the execution directory,
   but can exist in other directories as long as the relative paths are provided
   correctly. If the pattern matches multiple files, then
   :taskopt:`copy_files.dest` must be a directory.

.. taskopt:: copy_files.dest

   The destination where the files are to be copied.

copy_tree -- Recursively copy directories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This task takes an existing directory (``src``) and copies it to the
destination. Internally, this task uses :pythonlib:`copytree
<shutil.html#shutil.copytree>` function to copy the directory, please refer to
Python docs for more details.

.. warning::

   If the destination directory already exists, the directory is deleted before
   copying the contents of the source directory. Currently, this task does not
   provide a way to copy only non-existent files to the destination. Use with
   caution.

.. taskopt:: copy_tree.src

   The source directory that must be recursively copied.

.. taskopt:: copy_tree.dest

   The pathname for the new directory to be created.

.. taskopt:: copy_tree.ignore_patterns

   A list of Unix-style file patterns used to ignore files present in source
   directory when copying it to destination. A good example of this is to
   prevent copying the contents of :file:`polyMesh` when copying the contents of
   :file:`constant` from one case directory to another.

.. taskopt:: copy_tree.preserve_symlinks

   A Boolean flag indicating whether symbolic links are preserved when copying.
   Linux and Mac OSX only.

clean_case -- Clean a case directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use this task to clean up a case directory after a run. By default, this task
will preserve all YAML and python files found in the case directory as well as
the :file:`0/` directory. For example,

.. code-block:: yaml

   - clean_case:
       remove_zero: yes
       remove_mesh: no
       preserve: [ "0.org" ]

.. taskopt:: clean_case.remove_zero

   Boolean flag indicating whether the :file:`0/` directory should be removed.
   The default value is ``False``.

.. taskopt:: clean_case.remove_mesh

   Boolean flag indicating whether the :file:`constant/polyMesh` directory
   should be removed. The default value is ``False``.

.. taskopt:: clean_case.preserve

   A list of Unix-style file patterns that match files that should be preserved
   within the case directory.

process_logs -- Process solver outputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This task takes one mandatory argument :taskopt:`log_file
<process_logs.log_file>` that contains the outputs from a CFD run. The
time-histories of the residuals are extracted and output to files that can be
loaded by :program:`gnuplot`, or loaded in python using :numpy:`loadtxt` command
or using Pandas library. Users can also plot the residuals by using the
:taskopt:`plot_residuals <process_logs.plot_residuals>` option. For example,

.. code-block:: yaml

   - process_logs:
     log_file: pimpleSolver.log
     log_directory: pimpleSolver_logs

   - process_logs:
     log_file: simpleSolver.log
     plot_residuals: yes
     residuals_plot_file: residuals.pdf
     residuals_fields: [Ux, Uy, p]

.. taskopt:: process_logs.log_file

   The filename containing the solver residual ouputs. This parameter is
   mandatory.

.. taskopt:: process_logs.logs_directory

   The directory where the processed residual time-history outputs are stored.
   Default: :file:`logs` within the execution directory.

.. taskopt:: process_logs.plot_residuals

   Boolean flag indicating whether a plot of the convergence time-history is
   generated. Default value is ``False``.

.. taskopt:: process_logs.residuals_plot_file

   The file where the plot is saved. Default value is :file:`residuals.png`. The
   user can use an appropriate extension (e.g., ``.png``, ``.pdf``, ``.jpg``) to
   change the image format of the plot generated.

.. taskopt:: process_logs.residual_fields

   A list of fields that are plotted. If not provided, all fields available are
   plotted.

.. taskopt:: process_logs.plot_continuity_errors

   A Boolean flag indicating whether time-history of continuity errors are
   plotted along with residuals.

task_set -- Group tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``task_set`` groups a sub-set of tasks that can be executed in a different
case directory. :download:`Download <../data/caelus_task_set.yaml>` an example.

.. taskopt:: task_set.case_dir

   The path to a valid Caelus case directory where the sub-tasks are to be
   executed. This parameter is mandatory.

.. taskopt:: task_set.name

   A unique name to identify this task group.

.. taskopt:: task_set.tasks

   The list of sub-tasks. This list can contain any of the tasks that have been
   documented above.
