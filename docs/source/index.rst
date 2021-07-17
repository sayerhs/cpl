
Caelus Python Library (CPL)
###########################

.. only:: html

   :Version: |release|
   :Date: |today|

Caelus Python Library is a companion package for interacting with `OpenFOAM
<http://openfoam.com/>`_ and its derivative `Caelus CML
<http://www.caelus-cml.com>`_ open-source CFD packages. The library provides
utilities for pre and post-processing, as well as automating various aspects of
the CFD simulation workflow. Written in Python, it provides a consistent
user-interface across the three major operating systems Linux, Windows, and Mac
OS X ensuring that the scripts written in one platform can be quickly copied and
used on other platforms.

Like CML, CPL is also an open-source library released under the Apache License
Version 2.0 license. See `Apache License Version 2.0
<https://www.apache.org/licenses/LICENSE-2.0>`_ for more details on use and
distribution.

This documentation is split into two parts: a :ref:`user <user_manual>` and a
:ref:`developer <developer_manual>` manual. New users should start with the user
manual that provides an overview of the features and capabilities currently
available in CPL, the installation process and examples of usage. The developer
manual documents the application programming interface (API) and is useful for
users and developers looking to write their own python scripts to extend
functionality or add features to the library. See :ref:`user_intro` for more
details.


.. _user_manual:

User Manual
===========

.. toctree::
   :maxdepth: 5

   user/intro
   user/installation
   user/configuration
   user/cli_apps
   user/tasks
   user/tuts


.. _developer_manual:

Developer Manual
================

.. toctree::
   :maxdepth: 5

   dev/caelus



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

