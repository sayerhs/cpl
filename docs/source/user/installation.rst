.. _installation:

Installing Caelus Python Library (CPL)
======================================

CPL is a python package for use with `Caelus CML
<http://www.caelus-cml.com>`_ simulation suite. In addition to Caelus CML and
python, it also requires several scientific python libraries:

   - `NumPy <http://www.numpy.org>`_ -- Arrays, linear algebra
   - `Pandas <http://pandas.pydata.org>`_ -- Data Analysis library
   - `Matplotlib <https://matplotlib.org>`_ -- Plotting package

To ease the process of installation of all the required dependencies, this user
guide recommends the use of `Anaconda Python Distribution
<http://docs.continuum.io/anaconda/index>`_. This distribution provides a
comprehensive set of python packages necessary to get up and running with
CPL.

The default installation instructions use Python v3.6. However, CPL is
designed to work with both Python v2.7 and Py3k versions.

Install Anaconda
----------------

#. `Download the Anaconda installer
   <https://www.continuum.io/downloads>`_ for your operating system.

#. Execute the downloaded file and follow the installation
   instructions. It is recommended that you install the default
   packages.

#. Update the anaconda environment according to `installation
   instructions
   <http://conda.pydata.org/docs/install/full.html#install-instructions>`_


.. note::

   Make sure that you answer ``yes`` when the installer asks to add the
   installation location to your default PATH locations. Or else the following
   commands will not work. It might be necessary to open a new shell for the
   environment to be updated.


Install CPL
----------------

.. _install_dev_git:

Developer Source from Git
~~~~~~~~~~~~~~~~~~~~~~~~~

#. Obtain the CPL source from the public Git repository.

   .. code-block:: bash

      # Change to directory where you want to develop/store sources
      git clone https://bitbucket.org/appliedccm/CPL
      cd CPL

#. Create a custom conda environment

   .. code-block:: bash

      # Ensure working directory is CPL
      conda env create -f environment.yaml

   .. note::

      #. Developers interested in developing CPL might want to install the
         development environment available in :file:`etc/devenv.yaml`. This
         installs additional packages like ``sphinx`` for document generation,
         and ``pytest`` for running the test suite.

      #. By default, the environment created is named ``caelus-env`` when using
         :file:`environment.yaml` and ``caelus-dev`` when using
         :file:`etc/devenv.yaml`. The user can change the name of the
         environment by using `-n <env_name>` option in the previous command.

#. Activate the custom environment and install CPL within this environment

   .. code-block:: bash

      source activate caelus-env
      pip install .

   For *editable* development versions of CPL use ``pip install -e .``
   instead.

Building documentation
----------------------

A local version of this documentation can be built using sphinx. See
:ref:`install_dev_git` for more details on installing the developer environment
and sources.

.. code-block:: bash

   # Change working directory to CPL
   cd docs/

   # Build HTML documentation
   make html
   # View in browser
   open build/html/index.html

   # Build PDF documentation
   make latexpdf
   open build/latex/CPL.pdf

Running tests
-------------

The unit tests are written using `py.test
<https://docs.pytest.org/en/latest/>`_. To run the tests execute the following
command :command:`py.test`
