.. _installation:

Installing Caelus Python Library (CPL)
======================================

CPL is a python package for use with `Caelus CML <http://www.caelus-cml.com>`_
simulation suite. Therefore, it is assumed that users have a properly
functioning CML installation on their system. In addition to Caelus CML and
python, it also requires several scientific python libraries:

   - `NumPy <http://www.numpy.org>`_ -- Arrays, linear algebra
   - `Pandas <http://pandas.pydata.org>`_ -- Data Analysis library
   - `Matplotlib <https://matplotlib.org>`_ -- Plotting package

The quickest way to install CPL is to use the `official installer
<http://www.caelus-cml.com/download/>`_ provided by Applied CCM. Once installed,
please proceed to :ref:`check_install` to learn how to use CPL.

For users wishing to install CPL from the git repository, this user
guide recommends the use of `Anaconda Python Distribution
<http://docs.continuum.io/anaconda/index>`_. This distribution provides a
comprehensive set of python packages necessary to get up and running with CPL.
An alternate approach using Python *virtualenv* is described at the end of this
section, but will require some Python expertise on the part of the user.

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

Install CPL
-----------

#. Obtain the CPL source from the public Git repository.

   .. code-block:: console

      # Change to directory where you want to develop/store sources
      git clone https://bitbucket.org/appliedccm/CPL
      cd CPL

#. Create a custom conda environment

   .. code-block:: console

      # Ensure working directory is CPL
      conda env create -f etc/caelus2.yml

   .. note::

      #. Developers interested in developing CPL might want to install the
         development environment available in :file:`etc/caelus2-dev.yml`. This
         installs additional packages like ``sphinx`` for document generation,
         and ``pytest`` for running the test suite.

      #. By default, the environment created is named ``caelus2`` when using
         :file:`etc/caelus2.yml` and ``caelus-dev`` when using
         :file:`etc/caelus2-dev.yml`. The user can change the name of the
         environment by using `-n <env_name>` option in the previous command.

      #. Users wishing to use Python 3.x should replace :file:`etc/caelus2.yml`
         with :file:`etc/caelus3.yml`. Both ``caelus2`` and ``caelus3``
         environment can be used side by side for testing and development.

#. Activate the custom environment and install CPL within this environment

   .. code-block:: console

      source activate caelus2
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
to the following documentation for more assistance:

#. `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_
#. `VirtualEnvWrapper <https://virtualenvwrapper.readthedocs.io/en/latest/>`_

Prepare system for virtual environment
--------------------------------------

#. Install necessary packages

  .. code-block:: console

    # Install necessary packages
    pip install virtualenv virtualenvwrapper

  Windows users must use ``virtualenvwrapper-win`` instead of the
  ``virtualenvwrapper`` mentioned above. Alternately, you might want to install
  these packages via ``apt-get`` or ``yum``.

#. Update your `~/.bashrc` or `~/.profile` with the following lines:

   .. code-block:: console

      export WORKON_HOME=~/ENVS/
      source /usr/local/bin/virtualenvwrapper.sh

   Adjust the location of ``virtualenvwrapper.sh`` file according to your system
   installation location.

Useful virtualenvwrapper commands
`````````````````````````````````

* ``mkvirtualenv`` - Create a new virtual environment

* ``workon`` - Activate a previously created virtualenv, or switch between
  environments.

* ``deactivate`` - Deactive the current virtual environment

* ``rmvirtualenv`` - Delete an existing virtual environment

* ``lsvirtualenv`` - List existing virtual environments

Install CPL
-----------

#. Obtain the CPL source from the public Git repository.

   .. code-block:: console

      # Change to directory where you want to develop/store sources
      git clone https://bitbucket.org/appliedccm/CPL
      cd CPL

#. Create a virtual environment with all dependencies for CPL

   .. code-block:: console

      # Create a caelus Python 2.7 environment
      mkvirtualenv -a $(pwd) -r requirements.txt caelus2

#. Activate virtual environment and install CPL into it

   .. code-block:: console

      # Ensure that we are in the right environment
      workon caelus2
      pip install . # Install CPL within this environment

.. note::

   #. Use ``--system-site-packages`` with the ``mkvirtualenv`` command to reuse
      python modules installed in the system (e.g., via ``apt-get``) instead of
      reinstalling packages locally within the environment.

   #. Use ``mkvirtualenv --python=PYTHON_EXE`` to customize the python
      interpreter used by the virutal environment instead of the default python
      found in your path.

.. _check_install:

Check installation
~~~~~~~~~~~~~~~~~~

After installing CPL, please open a command line terminal and execute
:program:`caelus -h` to check if the installation process was completed
succesfully. Note that users who didn't use the installer provided by Applied
CCM might need to activate their *environment* before the ``caelus`` command is
available on their path. If everything was installed and configured
successfully, users should see a detailed help message summarizing the usage of
:program:`caelus`. At this stage, you can either learn about building
documentation and executing unit tests (provided with CPL) in the next sections
or skip to :ref:`configuration` to learn how to configure and use CPL.

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
:file:`etc/caelus2-dev.yml` (or :file:`etc/caelus3-dev.yml` for the Python v3.x
version).
