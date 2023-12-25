.. _installation:

Installing Caelus Python Library (CPL)
======================================

CPL is a python package for use with `OpenFOAM <https://openfoam.com>`_ or
`Caelus CML <http://www.caelus-cml.com>`_ simulation suite. Therefore, it is
assumed that users have a properly functioning OpenFOAM or CML installation on
their system. In addition to OpenFoAM/Caelus CML and python, it also requires
several scientific python libraries:

   - `NumPy <http://www.numpy.org>`_ -- Arrays, linear algebra
   - `Pandas <http://pandas.pydata.org>`_ -- Data Analysis library
   - `Matplotlib <https://matplotlib.org>`_ -- Plotting package

The quickey way to install CPL is to install through `Anaconda Python
Distribution <http://docs.continuum.io/anaconda/index>`_. This distribution
provides a comprehensive set of python packages necessary to get up and running
with CPL. Once installed, please proceed to :ref:`check_install` to learn how to
use CPL.

For users wishing to install CPL from the git repository, this user
guide recommends the use of Anaconda. An alternate approach using Python 
*virtualenv* is described at the end of this section, but will require some 
Python expertise on the part of the user.

The default installation instructions use Python v2.7. However, CPL is
designed to work with both Python v2.7 and Python v3.x versions.

Installing CPL with Anaconda Python Distribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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


.. _install_dev_git:

Install CPL from conda-forge (recommended)
------------------------------------------

#. Install CPL using the Anaconda package manager.

   .. code-block:: console

      conda install -c conda-forge caelus

Install CPL from source
-----------------------

#. Obtain the CPL source from the public Git repository.

   .. code-block:: console

      # Change to directory where you want to develop/store sources
      git clone https://bitbucket.org/appliedccm/CPL
      cd CPL

#. Create a custom conda environment

   .. code-block:: console

      # Ensure working directory is CPL
      conda env create -f etc/caelus3.yml

   .. note::

      #. Developers interested in developing CPL might want to install the
         development environment available in :file:`etc/caelus2-dev.yml`. This
         installs additional packages like ``sphinx`` for document generation,
         and ``pytest`` for running the test suite.

      #. By default, the environment created is named ``caelus`` when using
         :file:`etc/caelus3.yml` and ``caelus-dev`` when using
         :file:`etc/caelus3-dev.yml`. The user can change the name of the
         environment by using `-n <env_name>` option in the previous command.

#. Activate the custom environment and install CPL within this environment

   .. code-block:: console

      source activate caelus
      pip install .

   For *editable* development versions of CPL use ``pip install -e .``
   instead.

After completing this steps, please proceed to :ref:`check_install` to test that
your installation is working properly.


Alternate Installation -- Virtualenv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method is suitable for users who prefer to use the existing python
installations in their system (e.g., from ``apt-get`` for Linux systems). A
brief outline of the installation process is described here. Users are referred
to the `virtual environments docs
<https://docs.python.org/3/library/venv.html>`_ for more information.

Install CPL
-----------

#. Obtain the CPL source from the public Git repository.

   .. code-block:: console

      # Change to directory where you want to develop/store sources
      git clone https://bitbucket.org/appliedccm/CPL
      cd CPL

#. Create a virtual environment with all dependencies for CPL

   .. code-block:: console

      # Create virtual environment
      python3 -m venv --system-site-packages .venv

      # Activate virtual environment
      source .venv/bin/activate

      # Install dependencies
      python3 -m pip install -r requirements.txt

#. Activate virtual environment and install CPL into it

   .. code-block:: console

      # Ensure that we are in the right environment
      source .venv/bin/activate
      pip install . # Install CPL within this environment

.. _check_install:

Check installation
~~~~~~~~~~~~~~~~~~

After installing CPL, please open a command line terminal, activate the right
python environment, and execute :program:`caelus -h` to check if the
installation process was completed succesfully. If everything was installed and
configured successfully, users should see a detailed help message summarizing
the usage of :program:`caelus`. At this stage, you can either learn about
building documentation and executing unit tests (provided with CPL) in the next
sections or skip to :ref:`configuration` to learn how to configure and use CPL.

Building documentation
~~~~~~~~~~~~~~~~~~~~~~

A local version of this documentation can be built using sphinx. See
:ref:`install_dev_git` for more details on installing the developer environment
and sources.

.. code-block:: console

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
~~~~~~~~~~~~~

The unit tests are written using `py.test
<https://docs.pytest.org/en/latest/>`_. To run the tests executing
:command:`py.test tests` from the top-level CPL directory. Note that this will
require the user to have initialized the environment using
:file:`etc/caelus3-dev.yml`.
