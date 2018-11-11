# -*- coding: utf-8 -*-

"""\
Caelus/OpenFOAM Dictionary Implementation
-----------------------------------------
"""

import six
from ..utils import struct
from .printer import DictPrinter

class CaelusDict(struct.Struct):
    """Caelus Input File Dictionary"""

    def __str__(self):
        strbuf = six.StringIO()
        pprint = DictPrinter(strbuf)
        pprint(self)
        return strbuf.getvalue()
