#!/usr/bin/python
# ---------------------------------------------------------------------------
# Caelus 7.04
# ---------------------------------------------------------------------------

import glob
import os
import shutil

# Importing the required modules for Python
import subprocess
import sys

import Caelus

# Starting up the meshing and solving
print "Cleaning tutorial: cavity"

# Cleaning up the case
os.system('caelus-cleanCase.py')
os.system('caelus-clearPolyMesh.py')

