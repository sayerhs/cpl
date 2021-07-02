.. _tuts_cpl_io_user:

Mainpulating input files with CPL
=====================================

CPL provides a pythonic interface to read, create, modify, and write out input
files necessary for running simulations using OpenFOAM or CML executables within 
a case directory. Users can interact with input files as python objects and use 
python data structures and functions to manipulate them. The modified objects can 
then be written out to files and CPL will pretty-print the files in the apporpriate
locations in the case directory. Most OpenFOAM/CML objects have a one-to-one
correspondence with python data structures within CPL. For example, OpenFOAM
dictionaries are accessed as Python dictionaries, specifically an instance of
:class:`~caelus.io.caelusdict.CaelusDict` which provides both attribute and
dictionary-style access to entries. FOAM ``List<Scalar>`` data types are
accessible as NumPy arrays, whereas generic lists containing mixed datatype
entries (e.g., the `blocks` entry in :file:`blockMeshDict`) are represented as
lists.

.. currentmodule:: caelus.io.dictfile

This tutorial provides a walkthrough of using :mod:`caelus.io` module to read,
manipulate, and write out input files in a case directory. The code snippets
shown in this tutorial will use the ``ACCM_airFoil2D`` tutorial in the
:file:`${PROJECT_DIR}/tutorials/incompressible/simpleSolver/ras/ACCM_airFoil2D`
directory. To execute the example code snippets shown in this tutorial, it is
recommended that execute them from this case directory and have the following
modules loaded in your script or interactive shell

.. code-block:: python

   import numpy as np
   import caelus.io as cio

The most general interface to an input file is through the
:class:`DictFile` class. It provides three ways of creating
an input file object that can be manipulated using CPL in python scripts. Using
the constructor creates a default file object that can be populated by the
user. In most situations, however, the user would load a template file using
:meth:`~DictFile.read_if_present` or :meth:`~DictFile.load` functions. The
former as the name indicates will load the file if present in the case
directory, whereas the latter will generate an error if the file doesn't exist.
The first example will use :file:`system/controlDict` file to show how the user
can load, examine, and manipulate the contents of a simple input file.

.. code-block:: python

   # Load the controlDict file from the case directory
   cdict = cio.DictFile.load("system/controlDict")

   # Show the keywords present in the controlDict file
   print(cdict.keys())

   # Change the variable 'startFrom' to 'latestTime'
   cdict['startFrom'] = 'latestTime'

   # Change 'writeFormat' to 'binary
   cdict['writeFormat'] = 'binary'

   # Show the current state of the controlDict contents
   print(cdict)

   # Save the updated controlDict file to the case directory
   cdict.write()

The next example uses the :class:`DictFile` to modify the :file:`0/U`. For the
purposes of this demonstration, we will change the inflow conditions from
:math:`\alpha = 0^\circ` angle of attack to a flow at :math:`\alpha = 6^\circ`
angle of attack.

.. code-block:: python

   # Load the U field file
   ufile = cio.DictFile.load("0/U")

   # Access the internalField variable
   internal = ufile['internalField']

If you print out `ufile['internalField']` you will notice that it is an instance
of :class:`~caelus.io.dtypes.Field` that contains two attributes: ``ftype``
representing the field type (``uniform`` or ``nonuniform``), and ``value`` that
contains the value of the field. In this the present example, we will access the
uniform velocity field value and update it with the u and v velocities
corresponding to :math:`\alpha = 6^\circ`.

.. code-block:: python

   # Access the wind speed
   wspd = internal.value[0]

   # Compute u and v components
   aoa_rad = np.radians(6.0)
   uvel = wspd * np.cos(aoa_rad)
   vvel = wspd * np.sin(aoa_rad)

   # Update the velocity field
   internal.value[0] = uvel
   internal.value[1] = vvel

   # Update the inlet value also (note attribute-style access)
   inlet = ufile['boundaryField'].inlet
   inlet.value = internal.value

   # Check the current state of the 0/U file
   print(ufile)

   # Write the updated 0/U file
   ufile.write()


Specialized CPL classes for CML input files
-------------------------------------------

While :class:`DictFile` provides a generic interface to all input files, CPL
also defines specialized classes that provide additional functionality for those
specific input files. The available classes that provide customized
functionality are listed below

.. autosummary::
   :nosignatures:

   ControlDict
   FvSchemes
   FvSolution
   DecomposeParDict
   TransportProperties
   TurbulenceProperties
   RASProperties
   LESProperties
   BlockMeshDict

The specialized classes provide the ability to create default entries as well as
provide a limited amount of syntax checking to ensure that the keywords contain
acceptable values. It also allows attribute style access (in addition to
dictionary style access) for the keywords present in the input file. The
:meth:`~DictFile.read_if_present` method is really useful with the specialized
classes, as the user does not have to provide the file name, as shown below

.. code-block:: python

   # Load files from system directory
   cdict = cio.ControlDict.read_if_present()
   fvsol = cio.FvSolution.read_if_present()
   fvsch = cio.FvSchemes.read_if_present()

For example, when using the :class:`DictFile` interface with
:file:`system/controlDict` file, the user could assign any arbitrary value to
``startFrom``. However, when using the :class:`ControlDict`, CPL will raise an
error if the user provides invalid value

.. code-block:: python

   # Attempt to pass invalid value will raise a ValueError as shown below
   cdict.startFrom = "bananas"
   # ValueError: ControlDict: Invalid option for 'startFrom'. Valid options are:
   #	('firstTime', 'startTime', 'latestTime')

   # The keywords in file can be accessed either as attributes or keys
   print ( cdict.stopAt, cdict['stopAt'])


Accessing keywords with special characters
------------------------------------------

While most keywords can be accessed as attributes, certain OpenFOAM/CML keywords
contain invalid characters and therefore must be accessed as dictionary keys
only. The :file:`fvSolution` and :file:`fvSchemes` provide good examples of
such keywords.

.. code-block:: python

   # Accessing the divSchemes for specific equation must use dictionary style
   # access
   divU = fvsch.divSchemes["div(phi,U)"]

   # Accessing the "(k|omega|nuTilda)" solver in fvSolution
   turbSolver = fvsol.solvers['"(k|omega|nuTilda)"']

Note the nested quotation marks for the ``"(k|omega|nuTilda)"`` keyword.
OpenFOAM/CML requires the double quotes because keyword starts with a
non-alphabetical character. Wrapping the entire thing in single quotes protects
the double quotes within Python.

Input files for turbulence models
---------------------------------

.. code-block:: python

   # Load the TurbulenceProperties file
   tprops = cio.TurbulenceProperties.read_if_present()

   # Examine the type of turbulence model being used
   print(tprops.simulationType)

   # Get an instance of the model input file (returns None if laminar)
   rans = tprops.get_turb_file()

   # Show the model and coeffs
   print(rans.model)
   print(rans.coeffs)

   # Options common to both RASProperties and LESProperties
   rans.turbulence   # Flag indicating if turbulence is active
   rans.printCoeffs  # Flag indicating whether coeffs are printed

   # Switch to k-omega SST model
   rans.model = "kOmegaSST"
   # Note that coeffs has switched to 'kOmegaSSTCoeffs' present in input file
   print(rans.coeffs)

   # Turn curvature correction on (this updates kOmegaSSTCoeffs now)
   rans.coeffs.curvatureCorrection = "on"

   # Note, we can still access SpalartAllmarasCoeffs manually
   # However, need to use dictionary style access
   sacoeffs = rans['SpalartAllmarasCoeffs']

   # Can still change S-A coeffs if necessary
   sacoeffs.curvatureCorrection = 'off'

   # Save updated RASProperties file
   rans.write()

In the next example, we will change the turbulence model from RANS to LES and
let CPL generate a default LESProperties file for us.

.. code-block:: python

   # Load the TurbulenceProperties file
   tprops = cio.TurbulenceProperties.read_if_present()

   # Switch to LES model
   tprops.simulationType = "LESModel"

   # Get the default LESProperties file generated by CPL
   les = tprops.get_turb_file()

   # Show default values created by CPL
   print(les)

   # Set up the appropriate coefficients for Smagorinsky
   coeffs = les.coeffs
   coeffs.ce = 1.05
   coeffs.ck = 0.07

   # Write out the updated files
   les.write()
   tprops.write()
