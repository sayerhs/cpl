.. _tuts_caelus_sim:

Parametric runs using CPL
=========================

CPL provides two classes :class:`~caelus.run.case.CMLSimulation` and
:class:`~caelus.run.case.CMLSimCollection` that can be used to create workflows
that can automate the CFD analysis process. It also provides an implementation
of :class:`CMLSimCollection` called
:class:`~caelus.run.parametric.CMLParametricRun` that can be used to automate
running a parametric study over several variables and managing the analysis as a
group. These classes serve as simple examples for the user to derive sub-classes
from CPL to develop their own custom workflows.

The parametric run capability is also accessible from the command-line via
:program:`caelus_sim`. This tutorial provides a step-by-step walkthrough of
exercising CPL's parametric run capabilities through the command-line. This
tutorial will demonstrate an example of generating airfoil polars for a range of
angles of attack at different Reynolds numbers. In addition to varying, the
angle of attack and Reynolds number, it will also show how to specify other flow
parameters through CPL.


Preliminaries
~~~~~~~~~~~~~

To use CPL's parametric run interface, the user needs to provide a simulation
configuration file (in YAML format), and a case template directory (similar to
the one used with :program:`caelus clone` command).

To follow along with this tutorial, we recommend that the user download the
:download:`parametric run setup file
<../../data/parametric_demo/caelus_sim.yaml>` and a :download:`case template
<../../data/parametric_demo/airfoil_demo.zip>`. For the purposes of this
tutorial we will assume that the user is executing the commands from within
:file:`$HOME/run` directory. Once downloaded please unzip the zip file.

.. code-block:: console

   # Files downloaded for the tutorial walkthrough
   bash:/tmp/run$ ls
   airfoil_demo.zip caelus_sim.yaml

   # Unzip the file
   bash:/tmp/run$ unzip airfoil_demo.zip
   Archive:  airfoil_demo.zip
      creating: airfoil_template/
      creating: airfoil_template/0.orig/
     inflating: airfoil_template/0.orig/k
     inflating: airfoil_template/0.orig/nut
     inflating: airfoil_template/0.orig/omega
     inflating: airfoil_template/0.orig/p
     inflating: airfoil_template/0.orig/U
     inflating: airfoil_template/cmlControls
      creating: airfoil_template/constant/
      creating: airfoil_template/constant/polyMesh/
     inflating: airfoil_template/constant/polyMesh/boundary
     inflating: airfoil_template/constant/polyMesh/faces.gz
     inflating: airfoil_template/constant/polyMesh/neighbour.gz
     inflating: airfoil_template/constant/polyMesh/owner.gz
     inflating: airfoil_template/constant/polyMesh/points.gz
     inflating: airfoil_template/constant/RASProperties
     inflating: airfoil_template/constant/transportProperties
     inflating: airfoil_template/constant/turbulenceProperties
      creating: airfoil_template/system/
     inflating: airfoil_template/system/controlDict
     inflating: airfoil_template/system/decomposeParDict
     inflating: airfoil_template/system/fvSchemes
     inflating: airfoil_template/system/fvSolution

Preparing a case template directory
-----------------------------------

In order to simplify the process of setting up parametric run, CPL assumes that
all user-configurable entries are provided in :file:`cmlControls` within the
case directory. Other files within the case directory use the ``#include``
option to include this file and use variable replacement macro syntax
``$variable`` to interface with the parametric run utility. In this airfoil
demonstration example, a :file:`cmlControls` that will be used is shown below:

.. code-block:: C++
   :linenos:

   FoamFile
   {
       version     2.0;
       format      ascii;
       class       dictionary;
       object      "cmlControls";
   }

   // * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

   density       1.225;

   Uinf          15.0;

   chord         1.0;

   Re            1000000.0;

   aoa           0.0;

   turbKe        3.75e-07;

   velVector     (15.0 0.0 0.0);

   nuValue       1.0e7;

   turbulenceModel kOmegaSST;

   // ************************************************************************* //

An example of using this file to set the turbulence model in
:file:`constant/RASProperties` is shown below:

::

   FoamFile
   {
       version     2.0;
       format      ascii;
       class       dictionary;
       location    "constant";
       object      RASProperties;
   }
   // * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

   #include "../cmlControls"

   RASModel        $turbulenceModel;

   turbulence      on;

   printCoeffs     on;

   kMin            1.e-20;

   // ************************************************************************* //



Notice how the :file:`cmlControls` file is included in line 11, and the property
``RASModel`` is set with ``$turbulenceModel`` (see line 27 in
:file:`cmlControls` snippet above).

Inputs for setting up parametric run
------------------------------------

The first step to creating a parametric analysis directory structure is to
execute the :program:`caelus_sim setup` command. By default, this command will
attempt to load the analysis configuration from the :file:`caelus_sim.yaml`. The
user can, however, change this by providing an alternate file with the ``-f``
flag. The contents of the
:download:`caelus_sim.yaml <../../data/parametric_demo/caelus_sim.yaml>` used for
this demo is shown below.

.. literalinclude:: ../../data/parametric_demo/caelus_sim.yaml
   :language: yaml
   :linenos:


The input file must contain one section ``simulation`` that provides all the
information necessary for setting up and executing the parametric run. The
``simulation`` dictionary contains the following major sections:

``sim_name``

  The name of the parametric analysis group. The program creates
  a unique run directory with this name. This parameter can also be overridden
  from the command line.

``template``

  Details of the case template that will be used to create the individual case
  directories. It must contain one mandatory entry: ``path``, that is the path
  to the template case directory. In this demo we will use the
  ``airfoil_template`` that we unzipped from the :file:`airfoil_demo.zip`.
  Additional parameters are passed to control the cloning of the template
  directory and are similar to :program:`caelus clone` command.

``simulation_setup``

  This section contains the details of the parametric run. ``case_template`` is
  a template suitable to be processed by `python str.format() method
  <https://docs.python.org/3/library/string.html#format-string-syntax>`_.

  ``run_matrix`` contains the list of parametric combinations that will be run.
  In this example, we will run two angles of attack for each of the two Reynolds
  numbers specified. Each entry in the list generates all possible combinations
  of runs possible, and these are sub-groups of parametric runs. User can
  provide multiple entries in the list to generate additional custom
  combinations.

  ``constant_parameters``, if present, are variables that that will be populated
  in addition to the variable parameters (in ``run_matrix``) when setting up the
  case.

  Finally, ``apply_transforms`` is an optional section, that uses valid python
  code snippets to perform user-defined transformations to the variables in
  ``run_matrix`` and ``constant_parameters`` to generate dependent variables or
  perform additional processing. After transformation, by default, all variables
  introduced by the python code is extracted and passed along with
  ``constant_parameters`` and variables in ``run_matrix`` to
  :file:`cmlControls`. However, if the user has imported modules or defined
  functions, this could lead to error. So it is recommended that the user
  manually specify the variables to extracted through the ``extract_vars``
  option in ``apply_transforms`` section.


``run_configuration``

  This section contains the details on how each case is executed after setup. It
  has a general section that has information regarding parallel run setup etc.

  ``change_inputs`` lists changes to be performed to input files cloned from the
  template directory. This step is performed after setting up case directory,
  but before execution of any pre-processing or solve tasks.

  ``prep`` contains tasks (see :ref:`user_caelus_tasks`) that must be executed
  before decomposing and executing the case. Note that the user need not specify
  the ``decomposePar`` task, as this is handled automatically by the parametric
  run interface.

  ``solve`` indicates the name of the solver that is used to run these cases. It
  can also accept a list entry with multiple solvers (e.g., running
  ``potentialSolver`` before ``simpleSolver``, etc.)

  ``post`` is similar to ``prep`` but are tasks that are executed after a
  successful solver completion.

Setting up a parametric run
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that we have the requisite inputs for setting up a parametric run, we will
use :program:`caelus_sim setup` command to setup a case (see
:ref:`cli_apps_caelus_sim` for more details).

.. code-block:: console

   bash:/tmp/run$ caelus_sim setup
   INFO: Caelus Python Library (CPL) v0.1.1
   #
   # Output deleted
   #
   INFO: Successfully setup simulation: airfoil_demo (6)

On successful execution, you should see a new directory :file:`airfoil_demo`
that contains six Caelus case directories for the various combinations of
Reynolds number and angles of attack. User can query the status of the analysis
by executing the ``status`` sub-command.

.. code-block:: console

   bash:/tmp/run/airfoil_demo$ ls
   Re_1.0e+06      Re_2.0e+06      caelus_sim.yaml
   bash:/tmp/run/airfoil_demo$ caelus_sim status
   INFO: Caelus Python Library (CPL) v0.1.1

   Run status for: airfoil_demo
   Directory: /private/tmp/run/airfoil_demo
   ===============================================
   #. NAME                     STATUS
   ===============================================
   1. Re_1.0e+06/aoa_+00.00    Setup
   2. Re_1.0e+06/aoa_+02.00    Setup
   3. Re_2.0e+06/aoa_+00.00    Setup
   4. Re_2.0e+06/aoa_+02.00    Setup
   5. Re_1.0e+06/aoa_-04.00    Setup
   6. Re_1.0e+06/aoa_-02.00    Setup
   ===============================================
   TOTAL = 6; SUCCESS = 0; FAILED = 0
   ===============================================

For a description of the various status tags, please consult :ref:`caelus_sim
status <cli_caelus_sim_status>` documentation.

.. note::

   #. If you are running from a directory outside of :file:`airfoil_demo` then
      provide the case path using the ``-d`` option to :program:`caelus_sim
      status -d`. You don't need to provide this if you were, say, within
      :file:`airfoil_demo/Re_1.0e+06` directory or any of the subdirectories.

   #. Setup sub-command allows the user to immediately perform ``prep`` tasks or
      submit the ``solve`` jobs immediately upon setup using the ``-p`` or
      ``-s`` flags during the invocation of ``setup``.


Prep, solve, and post
~~~~~~~~~~~~~~~~~~~~~

Now that the cases as setup, the user can examine the auto-generated case
directories to ensure everything is setup properly and can *run* the simulation
by just invoking the ``solve`` sub-command. CPL will detect if pre-processing
and case decomposition haven't been performed and will perform these tasks. User
also has the option to explicitly invoke the ``prep`` task separately from
command line. Without any arguments, these sub-commands will choose all the
cases within a parametric run for execution. User can, however, pass shell-style
wildcard arguments to select a subset of cases where the command is executed. In
this tutorial, we will demonstrate this behavior by executing ``prep`` only on
the cases where :math:`Re = 2\times 10^6`.

.. code-block:: console

   #
   # Submit prep only for Re=2e6
   #
   bash:/tmp/run/airfoil_demo$ caelus_sim prep 'Re_2.0*/*'
   INFO: Caelus Python Library (CPL) v0.1.144-g41f57bc-dirty
   INFO: Executing pre-processing tasks for case: Re_2.0e+06/aoa_+00.00
   INFO: Writing Caelus input file: system/decomposeParDict
   INFO: Decomposing case: Re_2.0e+06/aoa_+00.00
   INFO: Executing pre-processing tasks for case: Re_2.0e+06/aoa_+02.00
   INFO: Writing Caelus input file: system/decomposeParDict
   INFO: Decomposing case: Re_2.0e+06/aoa_+02.00

   #
   # Check status of simulation
   #
   bash:/tmp/run/airfoil_demo$ caelus_sim status
   INFO: Caelus Python Library (CPL) v0.1.1-44-g41f57bc-dirty

   Run status for: airfoil_demo
   Directory: /private/tmp/run/airfoil_demo
   ===============================================
   #. NAME                     STATUS
   ===============================================
   1. Re_1.0e+06/aoa_+00.00    Setup
   2. Re_1.0e+06/aoa_+02.00    Setup
   3. Re_2.0e+06/aoa_+00.00    Prepped
   4. Re_2.0e+06/aoa_+02.00    Prepped
   5. Re_1.0e+06/aoa_-04.00    Setup
   6. Re_1.0e+06/aoa_-02.00    Setup
   ===============================================
   TOTAL = 6; SUCCESS = 0; FAILED = 0
   ===============================================

Note the use of single quotes around the wildcard arguments to prevent expansion
by the shell when parsing the command line.

In the next step, we will directly invoke ``solve`` on the positive angle of
attack cases for :math:`Re = 1\times 10^6` to demonstrate the automatic
invocation of ``prep`` if not already performed.

.. code-block:: console

   #
   # Submit solve only for positive aoa and Re=1e6
   #
   bash:/tmp/run/airfoil_demo$ caelus_sim solve 'Re_1.0*/aoa_+*'
   INFO: Caelus Python Library (CPL) v0.1.1
   INFO: Executing pre-processing tasks for case: Re_1.0e+06/aoa_+00.00
   INFO: Submitting solver (simpleSolver) for case: Re_1.0e+06/aoa_+00.00
   INFO: Executing pre-processing tasks for case: Re_1.0e+06/aoa_+02.00
   INFO: Submitting solver (simpleSolver) for case: Re_1.0e+06/aoa_+02.00

   #
   # Check status of simulation
   #
   bash:/tmp/run/airfoil_demo$ caelus_sim status
   INFO: Caelus Python Library (CPL) v0.1.1

   Run status for: airfoil_demo
   Directory: /private/tmp/run/airfoil_demo
   ===============================================
   #. NAME                     STATUS
   ===============================================
   1. Re_1.0e+06/aoa_+00.00    Solved
   2. Re_1.0e+06/aoa_+02.00    FAILED
   3. Re_2.0e+06/aoa_+00.00    Prepped
   4. Re_2.0e+06/aoa_+02.00    Prepped
   5. Re_1.0e+06/aoa_-04.00    Setup
   6. Re_1.0e+06/aoa_-02.00    Setup
   ===============================================
   TOTAL = 6; SUCCESS = 0; FAILED = 1
   ===============================================

.. note::

   For the purposes of demonstration, the ``endTime`` is ``controlDict`` is set
   to one timestep. Also a deliberate error was introduced in solve step to
   demonstrate the ``FAILED`` status flag.

User can execute the ``post`` step and it will only execute post-processing
actions on cases that have completed the solve.

.. code-block:: console

   #
   # Execute post-processing actions
   #
   bash:/tmp/run/airfoil_demo$ caelus_sim post
   INFO: Caelus Python Library (CPL) v0.1.1
   INFO: Executing post-processing tasks for case: Re_1.0e+06/aoa_+00.00
   WARNING: Re_1.0e+06/aoa_+02.00: No previous solve detected, skipping post
   WARNING: Re_2.0e+06/aoa_+00.00: No previous solve detected, skipping post
   WARNING: Re_2.0e+06/aoa_+02.00: No previous solve detected, skipping post
   WARNING: Re_1.0e+06/aoa_-04.00: No previous solve detected, skipping post
   WARNING: Re_1.0e+06/aoa_-02.00: No previous solve detected, skipping post

   #
   # Check status of simulation
   #
   bash:/tmp/run/airfoil_demo$ caelus_sim status
   INFO: Caelus Python Library (CPL) v0.1.1

   Run status for: airfoil_demo
   Directory: /private/tmp/run/airfoil_demo
   ===============================================
   #. NAME                     STATUS
   ===============================================
   1. Re_1.0e+06/aoa_+00.00    DONE
   2. Re_1.0e+06/aoa_+02.00    FAILED
   3. Re_2.0e+06/aoa_+00.00    Prepped
   4. Re_2.0e+06/aoa_+02.00    Prepped
   5. Re_1.0e+06/aoa_-04.00    Setup
   6. Re_1.0e+06/aoa_-02.00    Setup
   ===============================================
   TOTAL = 6; SUCCESS = 1; FAILED = 1
   ===============================================
