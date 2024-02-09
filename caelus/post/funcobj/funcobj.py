# -*- coding: utf-8 -*-

"""\
Core function object utilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implements the base classes upon with the concrete function object interfaces
are built on. :class:`FunctionObject` implements common methods used by all the
subclasses.

"""

import abc
import glob
import os
from pathlib import Path

from ...io.caelusdict import CaelusDict
from ...utils import osutils


class DictMeta(abc.ABCMeta):
    """Create property methods and add validation for properties.

    This metaclass implements the boilerplate code necessary to add
    getter/setters for various entries found in a Caelus input file. It expects
    a class variable ``_dict_properties`` that contains tuples for the various
    entries in the input file. The tuple can be of two forms:

      - (name, default_value)
      - (name, default_value, valid_values)
    """

    # pylint: disable=no-value-for-parameter

    def __init__(cls, name, bases, cdict, **kwargs):
        super(DictMeta, cls).__init__(name, bases, cdict)
        if "_dict_properties" in cdict:
            cls.process_properties(cdict["_dict_properties"])

    def process_properties(cls, proplist):
        """Create getters/setters for properties"""
        for plist in proplist:
            cls.process_property(plist)

    def process_property(cls, plist):
        """Process a property"""
        name = plist[0]
        options = plist[2] if len(plist) == 3 else None
        doc = "%s" % name

        def getter(self):
            """Getter"""
            return self.data.get(name, plist[1])

        if options:

            def setter(self, value):
                """Setter"""
                if not value in options:
                    raise ValueError(
                        "%s: Invalid option for '%s'. "
                        "Valid options are:\n\t%s"
                        % (cls.__name__, name, options)
                    )
                self.data[name] = value

        else:

            def setter(self, value):
                "Setter"
                self.data[name] = value

        setattr(cls, name, property(getter, setter, doc=doc))


class FuncObjMeta(DictMeta):
    """Specialization for Function objects"""

    def __call__(cls, *args, **kwargs):
        """Check if it is a concrete type"""
        if not hasattr(cls, "_funcobj_type"):
            raise RuntimeError(f"Cannot instantiate {cls.__name__}")
        return super().__call__(*args, **kwargs)


class FunctionObject(metaclass=FuncObjMeta):
    """Base class representing an OpenFOAM function object"""

    _run_control_opts = [
        'none',
        'timeStep',
        'writeTime',
        'runTime',
        'adjustableRunTime',
        'clockTime',
        'cpuTime',
        'onEnd',
    ]

    _dict_properties = [
        ('libs', None),
        ('region', 'region0'),
        ('enabled', True),
        ('log', True),
        ('timeStart', 0),
        ('timeEnd', None),
        ('executeControl', 'timeStep', _run_control_opts),
        ('executeInterval', 1),
        ('writeControl', 'timeStep', _run_control_opts),
        ('writeInterval', 1),
    ]

    @classmethod
    def funcobj_type(cls):
        """Return the string representing this functionObject type."""
        return getattr(cls, "_funcobj_type")

    @classmethod
    def create(cls, *, name, casedir=None, **kwargs):
        """Create a function object from scratch"""
        obj = cls.__new__(cls)
        obj.casedir = Path(casedir or os.getcwd())
        obj.name = name
        obj.data = CaelusDict()
        obj.data.type = obj._funcobj_type
        obj.data.libs = obj._funcobj_libs
        obj.data.update(kwargs)
        return obj

    def __init__(self, name, obj_dict, *, casedir=None):
        """Initialize object from input dictionary.

        Args:
            name (str): User-defined name for this object (in functions)
            obj_dict (CaelusDict): Input dictionary for this functionObject
            casedir (path): Path to the case directory (default: cwd)
        """
        self.casedir = Path(casedir or os.getcwd())
        self.name = name
        self.data = obj_dict

    @property
    def root(self):
        """Root path to the function object in postProcessing"""
        return self.casedir / "postProcessing" / self.name

    @property
    def times(self):
        """Return the list of time directories available"""
        with osutils.set_work_dir(self.root):
            return sorted(glob.glob("[0-9]*"), key=float, reverse=True)

    @property
    def latest_time(self):
        """Return the latest time available"""
        return self.times[0] if self.times else ""

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
