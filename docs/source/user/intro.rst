.. _user_intro:

Introduction
============

The primary motivation for CPL is to provide a platform-agnostic capability to
automate the CFD simulation workflow with OpenFOAM and Caelus CML packages. The
package is configurable to adapt to different user needs and system
configurations and can interact with multiple software versions simultaneous
without the need to source *environment* files (e.g., using
:file:`caelus-bashrc` or :file:`OpenFOAM/etc/bashrc` on Unix systems).

Some highlights of CPL include:

- The library is built using Python programming language and uses scientific
  python libraries (e.g., NumPy, Matplotlib).

  - Versions 2.0.0 and older support both python 2.7 and 3.x.
  - Version 2.0.0 requires python-3.6 or higher.
  - Version 3.0.0 reequires python-3.10 or higher.

- Uses `YAML <http://yaml.org>`_ format for configuration files and input files.
  The YAML files can be read, manipulated, and written out to disk using
  libraries available in several programming languages, not just Python.

- Provides modules and python classes to work with OpenFOAM and Caelus case
  directories, process and plot logs, etc. The API is documented to allow users
  to build custom workflows that are currently not part of CPL.

- A YAML-based *task* workflow capable of automating the mesh, pre-process,
  solve, post-process workflow on both local workstations as well as
  high-performance computing (HPC) systems with job schedulers.

Usage
-----

CPL is distributed under the terms Apache License Version 2.0 open-source
license. Users can install the package using `conda <https://conda.io>`_, or
access the `Git repository <https://bitbucket.org/appliedccm/cpl>`_ hosted on
BitBucket. Please follow :ref:`installation` for more details on how to install
CPL and its dependencies within an existing Python installation on your system.

Please contact the developers with questions, issues, or bug reports.

Contributing
------------

CPL is an open-source project and welcomes the contributions from the user
community. Users wishing to contribute should submit pull requests to the public
git repository.
