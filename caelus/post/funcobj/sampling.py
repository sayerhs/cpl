# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods

"""\
Sets and surfaces sampling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module implements the python interface to OpenFOAM's ``sets`` and
``surfaces`` sampling objects.

.. currentmodule: caelus.post.funcobj.sampling
.. autosummary::
   :nosignatures:

   SampledSets
   SampledSurfaces
   SampledSet
   SampledSurface

The different classes are illustrated using this example functionObject entry
in ``motorBike`` tutorial example::

   cuttingPlane
   {
       type            surfaces;
       libs            (sampling);
       writeControl    writeTime;

       surfaceFormat   vtk;
       fields          ( p U );

       interpolationScheme cellPoint;

       surfaces
       {
           yNormal
           {
               type            cuttingPlane;
               planeType       pointAndNormal;
               pointAndNormalDict
               {
                   point   (0 0 0);
                   normal  (0 1 0);
               }
               interpolate     true;
           }
       }
   }

When the above object is accessed via
:class:`~caelus.post.funcobj.functions.PostProcessing` class, the
``cuttingPlane`` object is represented by :class:`SampledSurfaces`, and the
``yNormal`` object is represented by :class:`SampledSurface` instance. Similar
relationship exists between :class:`SampledSets` and :class:`SampledSet`.

"""

import abc
import itertools
from pathlib import Path

import pandas as pd

from ...utils.vtk_helpers import pyvista
from .funcobj import DictMeta, FunctionObject


class SampledData(metaclass=DictMeta):
    """Base class for a single sampling object."""

    def __init__(self, name, fobj_dict, parent):
        """Initialize data from input dictionary.

        Args:
            name (str): User-defined name for this sampling instance
            fobj_dict (CaelusDict): Input parameter dictionary
            parent (Sampling): Parent collection instance
        """
        #: User-defined name for this sampling instance
        self.name = name
        #: Input dictionary containing data for this instance
        self.data = fobj_dict
        #: The parent sets/surfaces group instance
        self.parent = parent

    @property
    def fields(self):
        """Return the names of fields requested by user"""
        return self.data.get("fields", self.parent.fields)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"


class SampledSet(SampledData):
    """A concrete ``set`` instance.

    Currently only ``raw``, ``vtk``, and ``csv`` formats are supported for
    ``setFormat`` if the user intends to load the dataset through this class.

    Example:
      >>> post = PostProcessing()      # Access post-processing instance
      >>> sets = post['sampledSets1']  # Get the sets group
      >>> probes = sets['probe1']      # Access line probe data
      >>> df = probes()                # Get dataframe for latest time
      >>> df1 = probes('10')           # Get dataframe for different time
    """

    _dict_properties = [
        (
            'type',
            None,
            (
                'uniform',
                'face',
                'midPoint',
                'midPointAndFace',
                'cloud',
                'patchCloud',
                'patchSeed',
                'polyLine',
                'triSurfaceMeshPointSet',
            ),
        ),
        ('axis', None, "x y z xyz distance".split()),
        ('points', None),
    ]

    def __init__(self, name, fobj_dict, parent):
        """Initialize data from input dictionary.

        Args:
            name (str): User-defined name for this sampling instance
            fobj_dict (CaelusDict): Input parameter dictionary
            parent (Sampling): Parent collection instance
        """
        super().__init__(name, fobj_dict, parent)
        self._cache = {}

    @property
    def num_coord_cols(self):
        """Return the number of expected columns for coordinates.

        If the ``axis`` is ``xyz`` then returns 3, else returns 1 for all other
        axis options.
        """
        return 3 if self.axis == "xyz" else 1

    @property
    def coord_cols(self):
        """Return names of the coordinates column.

        If ``axis == "xyz"`` then returns a list of 3 columns, else returns the
        column name defined by axis.
        """
        return "x y z".split() if self.axis == "xyz" else [self.axis]

    def _file_fmt(self):
        """Return a shell wildcard glob expression for files.

        The wildcard glob is based on the user-defined name for this set
        instance and the ``setFormat`` option.
        """
        ext_map = dict(
            raw=".xy",
            vtk=".vtk",
            csv=".csv",
        )
        outfmt = self.parent.setFormat
        if outfmt not in ext_map:
            raise RuntimeError(f"{outfmt} not yet supported")
        return f"{self.name}*{ext_map[outfmt]}"

    def _extract_field_names(self, fname):
        """Extract field names from a file name."""
        skip = len(self.name) + 1
        filtered = fname.stem[skip:]
        return filtered.split("_")

    def _process_field_names(self, fields, ncols):
        """Return names for components.

        Args:
            fields (list): List of field names in the file
            ncols (int): Number of columns seen per field

        Return:
            list: A list of column names for a data file.
        """
        if ncols == 3:
            return [
                f"{x}_{y}"
                for x, y in itertools.product(fields, "x y z".split())
            ]

        return [f"{x}_{y}" for x, y in itertools.product(fields, range(ncols))]

    def _load_raw_file(self, fname):
        """Load a raw format file.

        Loads files of the format ``<name>_<field>.xy``.

        Args:
            fname (str): Name of the file to read.

        Returns:
            pd.DataFrame: Pandas dataframe with the dataset.
        """
        coords = self.coord_cols
        fields = self._extract_field_names(fname)
        df = pd.read_table(fname, delimiter=" ", index_col=False, header=None)

        ncols = (len(df.columns) - len(coords)) / len(fields)
        fnames = (
            fields if ncols == 1 else self._process_field_names(fields, ncols)
        )
        df.columns = coords + fnames
        return df

    def _load_vtk_file(self, fname):
        """Load a legacy VTK file and return data.

        Loads files of the format ``<name>_<field>.vtk``.

        Args:
            fname (str): Name of the file to read.

        Returns:
            pd.DataFrame: Pandas dataframe with the dataset.
        """
        mesh = pyvista().read(fname)
        df = pd.DataFrame(mesh.points, columns="x y z".split())
        for k in mesh.point_data.keys():
            val = mesh.point_data[k]
            if val.ndim > 1:
                fnames = self._process_field_names(k, val.shape[-1])
                df.loc[:, fnames] = val
            else:
                df[k] = val
        return df

    def __call__(self, time=None):
        """Load data for this set at a given time."""
        reader_map = dict(
            raw=self._load_raw_file,
            vtk=self._load_vtk_file,
        )

        dtime = str(time) if time else self.parent.latest_time
        if dtime in self._cache:
            return self._cache[dtime]

        dpath = Path(self.parent.root) / dtime
        if not dpath.exists():
            raise FileNotFoundError(f"No data found: {dpath}")

        flist = dpath.glob(self._file_fmt())
        file_fmt = self.parent.setFormat
        file_reader = reader_map[file_fmt]
        frames = [file_reader(ff) for ff in flist]

        if not frames:
            raise RuntimeError(f"Error loading data for {self.name}")

        df = pd.concat(frames, axis=1)
        df1 = df.loc[:, ~df.columns.duplicated()]
        self._cache = dict([(dpath.stem, df1)])
        return df1


class SampledSurface(SampledData):
    """A concrete ``surface`` instance.

    Currently only ``vtk`` output format is supported for reading data. A
    ``pyvista.Mesh`` instance is returned and can be interacted using
    ``vtk.vtkPolyData`` methods.

    Example:
      >>> post = PostProcessing()          # Access post-processing instance
      >>> surfaces = post['cuttingPlane']  # Get the surfaces group
      >>> plane = surfaces['yNormal']      # Access plane data
      >>> patch = plane()                  # Get dataframe for latest time
      >>> patch1 = plane('10')             # Get dataframe for different time

    """

    _dict_properties = [
        ('type', None),
    ]

    def __init__(self, name, fobj_dict, parent):
        """Initialize data from input dictionary.

        Args:
            name (str): User-defined name for this sampling instance
            fobj_dict (CaelusDict): Input parameter dictionary
            parent (Sampling): Parent collection instance
        """
        super().__init__(name, fobj_dict, parent)
        self._cache = {}

    def __call__(self, time=None):
        """Return the dataframe associated with a given time."""
        dtime = str(time) if time else self.parent.latest_time
        if dtime in self._cache:
            return self._cache[dtime]

        dpath = Path(self.parent.root) / dtime
        fname = dpath / (self.name + ".vtp")
        if not fname.exists():
            raise FileNotFoundError(f"Surface output not found: {fname}")

        mesh = pyvista().read(fname)
        self._cache = dict([(dpath.stem, mesh)])
        return mesh


class Sampling(FunctionObject):
    """Base class for sets and surfaces sampling groups."""

    _funcobj_libs = ["sampling"]

    _dict_properties = [
        ('fields', None),
        (
            'interpolationScheme',
            'cell',
            "cell cellPoint cellPointFace pointMVC cellPatchConstrained".split(),
        ),
    ]

    def __init__(self, name, obj_dict, *, casedir=None):
        super().__init__(name, obj_dict, casedir=casedir)
        #: Mapping of sampling instances to their names.
        self.samples = {}

    def keys(self):
        """Return the names of the sampling entries"""
        return self.samples.keys()

    def __getitem__(self, key):
        """Return the instance corresponding to user given name."""
        return self.samples[key]


class SampledSets(Sampling):
    """A ``sets`` functionObjects entry.

    This class provides an interface to a group of sampled set instances. The
    instances are of type :class:`SampledSet`.

    """

    _funcobj_type = "sets"

    _dict_properties = [
        ('setFormat', 'raw', "raw gnuplot xmgr jplot vtk ensight csv".split()),
    ]

    def __init__(self, name, obj_dict, *, casedir=None):
        super().__init__(name, obj_dict, casedir=casedir)

        for entry in self.data.sets:
            for k, v in entry.items():
                self.samples[k] = SampledSet(k, v, self)


class SampledSurfaces(Sampling):
    """A ``surfaces`` functionObjects entry.

    This class provides an interface to a group of sampled surface (planes or
    patches) instances. The instances are of type :class:`SampledSurface`.

    """

    _funcobj_type = "surfaces"

    _dict_properties = [
        ('surfaceFormat', 'vtk'),
    ]

    def __init__(self, name, obj_dict, *, casedir=None):
        super().__init__(name, obj_dict, casedir=casedir)

        surfaces = self.data.surfaces
        if isinstance(surfaces, list):
            for surf in surfaces:
                for k, v in surf.items():
                    self.samples[k] = SampledSurface(k, v, self)
        else:
            for k, v in surfaces.items():
                self.samples[k] = SampledSurface(k, v, self)
