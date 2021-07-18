# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods

"""\
Point and surface sampling
--------------------------
"""

import abc
import itertools
from pathlib import Path

import pandas as pd

from .funcobj import FunctionObject, DictMeta
from ...utils.vtk_helpers import pyvista


class SampledData(metaclass=DictMeta):
    """Base class for single sampling object"""

    def __init__(self, name, fobj_dict, parent):
        """
        Args:
            name (str): Name of this sample set
            fobj_dict (CaelusDict): Parameters
        """
        self.name = name
        self.data = fobj_dict
        self.parent = parent

    @property
    def fields(self):
        """Get the names of the fields"""
        return self.data.get("fields", self.parent.fields)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"


class SampledSet(SampledData):
    """Object representing a single set"""

    _dict_properties = [
        ('type', None,
         ('uniform', 'face', 'midPoint', 'midPointAndFace',
          'cloud', 'patchCloud', 'patchSeed', 'polyLine',
          'triSurfaceMeshPointSet')),
        ('axis', None, "x y z xyz distance".split()),
        ('points', None),
    ]

    def __init__(self, name, fobj_dict, parent):
        super().__init__(name, fobj_dict, parent)
        self._cache = {}

    @property
    def num_coord_cols(self):
        """Return the number of expected columns for coordinates"""
        return 3 if self.axis == "xyz" else 1

    @property
    def coord_cols(self):
        """Return names of the coordinates column"""
        return "x y z".split() if self.axis == "xyz" else [self.axis]

    def _file_fmt(self):
        """Return the file format glob"""
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
        """Extract field names from a file name"""
        skip = len(self.name) + 1
        filtered = fname.stem[skip:]
        return filtered.split("_")

    def _process_field_names(self, fields, ncols):
        """Return names for components"""
        if ncols == 3:
            return [f"{x}_{y}" for x, y in
                    itertools.product(fields, "x y z".split())]

        return [f"{x}_{y}" for x, y in
                itertools.product(fields, range(ncols))]

    def _load_raw_file(self, fname):
        """Load a raw format file"""
        coords = self.coord_cols
        fields = self._extract_field_names(fname)
        df = pd.read_table(fname, delimiter=" ", index_col=False)

        ncols = (len(df.columns) - len(coords)) / len(fields)
        fnames = (fields
                  if ncols == 1
                  else self._process_field_names(fields, ncols))
        df.columns = coords + fnames
        return df

    def _load_vtk_file(self, fname):
        """Load a legacy VTK file and return data"""
        mesh = pyvista().read(fname)
        df = pd.DataFrame(mesh.points, columns="x y z".split())
        for k in mesh.point_arrays.keys():
            val = mesh.point_arrays[k]
            if val.ndim > 1:
                fnames = self._process_field_names(k, val.shape[-1])
                df.loc[:, fnames] = val
            else:
                df[k] = val
        return df

    def __call__(self, time=None):
        """Return the dataframe associated with a given time."""
        reader_map = dict(
            raw=self._load_raw_file,
            vtk=self._load_vtk_file,
        )

        if time in self._cache:
            return self._cache[time]

        dtime = str(time) if time else self.parent.latest_time
        dpath = Path(self.parent.root) / dtime
        if not dpath.exists():
            raise FileNotFoundError(
                f"No data found: {dpath}")

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
    """Single sampled surface entry"""

    _dict_properties = [
        ('type', None),
    ]

    def __init__(self, name, fobj_dict, parent):
        super().__init__(name, fobj_dict, parent)
        self._cache = {}

    def __call__(self, time=None):
        """Return the dataframe associated with a given time."""
        if time in self._cache:
            return self._cache[time]

        dtime = str(time) if time else self.parent.latest_time
        dpath = Path(self.parent.root) / dtime
        fname = dpath / (self.name + ".vtp")
        if not fname.exists():
            raise FileNotFoundError(
                f"Surface output not found: {fname}")

        mesh = pyvista().read(fname)
        self._cache = dict([(dpath.stem, mesh)])
        return mesh


class Sampling(FunctionObject):
    """Base class for sampling types"""

    _funcobj_libs = ["sampling"]

    _dict_properties = [
        ('fields', None),
        ('interpolationScheme', 'cell',
         "cell cellPoint cellPointFace pointMVC cellPatchConstrained".split())
    ]


class SampledSets(Sampling):
    """Sampling probes in computational domain"""

    _funcobj_type = "sets"

    _dict_properties = [
        ('setFormat', 'raw',
         "raw gnuplot xmgr jplot vtk ensight csv".split()),
    ]

    def __init__(self, name, obj_dict, *, casedir=None):
        super().__init__(name, obj_dict, casedir=casedir)
        self.sets = {}

        for entry in self.data.sets:
            for k, v in entry.items():
                self.sets[k] = SampledSet(k, v, self)


class SampledSurfaces(Sampling):
    """Sampling surface entries in computational domain"""

    _funcobj_type = "surfaces"

    _dict_properties = [
        ('surfaceFormat', 'vtk'),
    ]

    def __init__(self, name, obj_dict, *, casedir=None):
        super().__init__(name, obj_dict, casedir=casedir)
        self.surfaces = {}

        for k, v in self.data.surfaces.items():
            self.surfaces[k] = SampledSurface(k, v, self)
