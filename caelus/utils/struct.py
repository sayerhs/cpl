# -*- coding: utf-8 -*-

"""\
Struct Module
-------------

Implements :class:`~caelus.utils.struct.Struct`.

"""

from collections import OrderedDict, MutableMapping, Mapping

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

class Struct(OrderedDict, MutableMapping): # pylint: disable=too-many-ancestors
    """Dictionary that supports both key and attribute access.

    Struct is inspired by Matlab ``struct`` data structure that is intended to
    support both key and attribute access. It has the following features:

       #. Preserves ordering of members as initialized
       #. Provides attribute and dictionary-style lookups
    """

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
