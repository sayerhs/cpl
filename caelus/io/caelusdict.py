# -*- coding: utf-8 -*-
# pylint: disable=protected-access, import-outside-toplevel

"""\
Caelus/OpenFOAM Dictionary Implementation
-----------------------------------------
"""

import re

import six

from ..config import cmlenv
from ..utils import osutils, struct
from . import dtypes
from .printer import DictPrinter


class CaelusDict(struct.Struct):
    """Caelus Input File Dictionary"""

    def __str__(self):
        strbuf = six.StringIO()
        pprint = DictPrinter(strbuf)
        pprint(self)
        return strbuf.getvalue()

    def _foam_load_include(self, fname, env=None):
        """Load an include file with given name"""
        # Prevent circular imports
        from .dictfile import DictFile

        fname = fname.strip('"')
        fname = osutils.abspath(fname)
        out = DictFile.load(filename=fname).data
        tmp = out._foam_expand_includes(env)
        return tmp

    def _foam_load_etc_include(self, fname, env=None):
        """Load an `includeEtc` directive"""
        cenv = env or cmlenv.cml_get_version()
        efile = cenv.etc_file(fname.strip('"'))
        return self._foam_load_include(efile)

    def _foam_expand_includes(self, env=None):
        """Expand all macros/include directives"""

        def has_includes(din):
            """Check whether a dictionary has include directive"""
            return any(
                isinstance(dval, dtypes.Directive)
                and "#include" in dval.directive
                for dval in din.values()
            )

        def _update(din, dout):
            if has_includes(din):
                dout.update(din._foam_expand_includes(env))
            else:
                for k, v in din.items():
                    if isinstance(v, CaelusDict):
                        _update(v, dout.setdefault(k, CaelusDict()))
                    else:
                        dout[k] = v

        out = self.__class__()
        cenv = env or cmlenv.cml_get_version()

        for k, val in self.items():
            if isinstance(val, CaelusDict):
                dout = out.setdefault(k, CaelusDict())
                _update(val, dout)
            elif (
                isinstance(val, dtypes.Directive)
                and val.directive == "#includeEtc"
            ):
                out.update(self._foam_load_etc_include(val.value, cenv))
            elif (
                isinstance(val, dtypes.Directive)
                and val.directive == "#include"
            ):
                out.update(self._foam_load_include(val.value, cenv))
            elif (
                isinstance(val, dtypes.Directive)
                and val.directive == "#includeIfPresent"
                and osutils.path_exists(val.value.strip('"'))
            ):
                out.update(self._foam_load_include(val.value, cenv))
            else:
                out[k] = val
        return out

    def _process_removes(self):
        """Process ``#remove`` directives"""
        keys = list(self.keys())
        removes = []
        for k in keys:
            val = self[k]
            if isinstance(val, dtypes.Directive) and (
                val.directive == "#remove"
            ):
                keyre = re.compile(val.value.strip('"'))
                removes.append(keyre)
                self.pop(k)
        keys = list(self.keys())
        for k in keys:
            for krexp in removes:
                if krexp.match(k) and k in self:
                    self.pop(k)
        return self

    def _foam_expand_macros(self, root=None):
        """Expand all dictionary macros"""
        _root = root or []
        keys = list(self.keys())

        # Perform substitutions recursively
        for ii, k in enumerate(keys):
            val = self[k]
            if isinstance(val, dtypes.MacroSubstitution):
                kk = val.value.strip('"${}')
                found = False
                krem = keys[ii:]
                for dd in reversed(_root):
                    if kk not in dd:
                        continue
                    sdict = dd[kk]
                    for kkk, vvv in sdict.items():
                        if kkk not in krem:
                            self[kkk] = vvv
                    found = True
                    break
                if not found:
                    # raise ValueError(f"Cannot substitute {val.value}")
                    print(f"Key not found: {val.value}")
                else:
                    self.pop(k)
            elif isinstance(val, CaelusDict):
                val._foam_expand_macros(_root + [self])

        self._process_removes()
        return self
