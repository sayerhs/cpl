# -*- coding: utf-8 -*-

"""\
Struct Module
-------------

Implements :class:`~caelus.utils.struct.Struct`.

"""

from collections import OrderedDict, MutableMapping, Mapping
from abc import ABCMeta
import yaml
import six
import numpy as np

def _merge(this, that):
    """Recursive merge from *that* mapping to *this* mapping

    A utility function to recursively merge entries. New entries are added, and
    existing entries are updated.

    Args:
        this (dict): Mapping that is updated
        that (dict): Mapping to be merged. Unmodified within the function
    """
    this_keys = frozenset(this)
    that_keys = frozenset(that)

    # Items only in 'that' dict
    for k in (that_keys - this_keys):
        this[k] = that[k]

    for k in (this_keys & that_keys):
        vorig = this[k]
        vother = that[k]

        # pylint: disable=bad-continuation
        if (isinstance(vorig, Mapping) and
            isinstance(vother, Mapping) and
            (id(vorig) != id(vother))):
            _merge(vorig, vother)
        else:
            this[k] = vother

def merge(a, b, *args):
    """Recursively merge mappings and return consolidated dict.

    Accepts a variable number of dictionary mappings and returns a new
    dictionary that contains the merged entries from all dictionaries. Note
    that the update occurs left to right, i.e., entries from later dictionaries
    overwrite entries from preceeding ones.

    Returns:
        dict: The consolidated map
    """
    out = a.__class__()
    _merge(out, a)
    _merge(out, b)

    for c in args:
        _merge(out, c)

    return out

def gen_yaml_decoder(cls):
    """Generate a custom YAML decoder with non-default mapping class

    Args:
        cls: Class used for mapping
    """
    def struct_constructor(loader, node):
        """Custom constructor for Struct"""
        return cls(loader.construct_pairs(node))

    # pylint: disable=too-many-ancestors
    class StructYAMLLoader(yaml.Loader):
        """Custom YAML loader for Struct data"""

        def __init__(self, *args, **kwargs):
            yaml.Loader.__init__(self, *args, **kwargs)
            self.add_constructor(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                struct_constructor)

    return StructYAMLLoader

def gen_yaml_encoder(cls):
    """Generate a custom YAML encoder with non-default mapping class

    Args:
        cls: Class used for mapping
    """
    def struct_representer(dumper, data):
        """Convert Struct to dictionary for YAML"""
        return dumper.represent_dict(list(data.items()))

    def numpy_representer(dumper, data):
        """Convert numpy arrays to YAML"""
        return dumper.represent_list(data.tolist())

    def numpy_scalar_representer(dumper, data):
        """Converty numpy dtypes to YAML"""
        if isinstance(data, np.int64):
            return dumper.represent_int(int(data))
        return dumper.represent_float(float(data))

    # pylint: disable=too-many-ancestors
    class StructYAMLDumper(yaml.Dumper):
        """Custom YAML dumper for Struct data"""

        def __init__(self, *args, **kwargs):
            yaml.Dumper.__init__(self, *args, **kwargs)
            self.add_representer(cls, struct_representer)
            self.add_representer(np.ndarray,
                                 numpy_representer)
            self.add_representer(np.float_,
                                 numpy_scalar_representer)
            self.add_representer(np.int_,
                                 numpy_scalar_representer)

    return StructYAMLDumper

class StructMeta(ABCMeta):
    """YAML interface registration

    Simplify the registration of custom yaml loader/dumper classes for Struct
    class hierarchy.
    """

    def __new__(mcls, name, bases, cdict):
        yaml_decoder = cdict.pop("yaml_decoder", None)
        yaml_encoder = cdict.pop("yaml_encoder", None)
        cls = super(StructMeta, mcls).__new__(mcls, name, bases, cdict)
        cls.yaml_decoder = yaml_decoder or gen_yaml_decoder(cls)
        cls.yaml_encoder = yaml_encoder or gen_yaml_encoder(cls)
        return cls

# pylint: disable=too-many-ancestors
@six.add_metaclass(StructMeta)
class Struct(OrderedDict, MutableMapping):
    """Dictionary that supports both key and attribute access.

    Struct is inspired by Matlab ``struct`` data structure that is intended to
    support both key and attribute access. It has the following features:

       #. Preserves ordering of members as initialized
       #. Provides attribute and dictionary-style lookups
       #. Read/write YAML formatted data
    """

    @classmethod
    def from_yaml(cls, stream):
        """Initialize mapping from a YAML string.

        Args:
            stream: A string or valid file handle

        Returns:
            Struct: YAML data as a python object
        """
        return cls(yaml.load(stream, Loader=cls.yaml_decoder))

    @classmethod
    def load_yaml(cls, filename):
        """Load a YAML file

        Args:
            filename (str): Absolute path to YAML file

        Returns:
            Struct: YAML data as python object
        """
        with open(filename, 'r') as fh:
            return cls.from_yaml(fh)

    def _getattr(self, key):
        return super(Struct, self).__getattribute__(key)

    def _setattr(self, key, value):
        super(Struct, self).__setattr__(key, value)

    # pylint: disable=signature-differs
    def __setitem__(self, key, value):
        # pylint: disable=bad-continuation
        if (isinstance(value, Mapping) and
            not isinstance(value, Struct)):
            out = self.__class__()
            _merge(out, value)
            super(Struct, self).__setitem__(key, out)
        else:
            super(Struct, self).__setitem__(key, value)

    def __setattr__(self, key, value):
        # Workaround for Python 2.7 OrderedDict
        if not key.startswith('_OrderedDict'):
            self[key] = value
        else:
            super(Struct, self).__setattr__(key, value)

    def __getattr__(self, key):
        if key not in self:
            raise AttributeError("No attribute named "+key)
        else:
            return self[key]

    def merge(self, *args):
        """Recursively update dictionary

        Merge entries from maps provided such that new entries are added and
        existing entries are updated.
        """
        for other in args:
            _merge(self, other)

    def to_yaml(self, stream=None, default_flow_style=False, **kwargs):
        """Convert mapping to YAML format.

        Args:
            stream (file): A file handle where YAML is output

            default_flow_style (bool):
                - False - pretty printing
                - True  - No pretty printing
        """
        return yaml.dump(self, stream=stream,
                         Dumper=self.__class__.yaml_encoder,
                         default_flow_style=default_flow_style,
                         **kwargs)
