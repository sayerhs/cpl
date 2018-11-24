# -*- coding: utf-8 -*-

"""
JSON Encoding Helper Classes for CPL
------------------------------------
"""

import json
import numpy as np
from .struct import Struct

class CPLJsonEncoder(json.JSONEncoder):
    """JSON convertor for classes used in CPL"""

    def default(self, obj):
        """Conversion rules"""
        if isinstance(obj, JSONSerializer):
            return obj.to_json()
        elif isinstance(obj, Struct):
            return obj.items()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return json.JSONEncoder.default(self, obj)

class JSONSerializer(object):
    """A mixin class to serialize CPL classes"""

    #: JSON dumper instance, customize this for derived classes
    _json_dumper_ = CPLJsonEncoder
    #: Public members that are serialized for this class
    _json_public_ = None

    #: (member, function) mapping for members that are transformed before
    #  serializing
    _json_mod_map_ = None

    @classmethod
    def json_file(cls):
        """Filename for serialization"""
        return "." + cls.__name__.lower() + ".json"

    def encode(self, **kwargs):
        """Encode the object into a JSON string

        The ``kwargs`` passed are passed directly to json.dumps method

        Returns:
            str: Valid JSON data
        """
        return json.dumps(self.to_json(),
                          cls=self._json_dumper_, **kwargs)

    def to_json(self):
        """Return a json serializable object"""
        public = self._json_public_ or []
        modifiers = self._json_mod_map_ or dict()

        retval = dict()
        for key in public:
            retval[key] = getattr(self, key, None)
        for key, modfunc in modifiers.items():
            retval[key] = modfunc(getattr(self, key, None))
        return retval
