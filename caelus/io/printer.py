# -*- coding: utf-8 -*-

"""\
Caelus Input File Pretty-printer
--------------------------------
"""

import sys
import re
from collections import Mapping
from contextlib import contextmanager

import numpy as np

from . import dtypes
from ..utils import osutils
from ..version import version

file_banner = r"""/*---------------------------------------------------------------------------*\
 * Caelus (http://www.caelus-cml.com)
 *
 * Caelus Python Library (CPL) %(version)s
 * Auto-generated on: %(timestamp)s
 *
\*---------------------------------------------------------------------------*/

"""

header_separator = """\
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

"""

eof_separator = """\
// ************************************************************************* //
"""

@contextmanager
def foam_writer(filename, header=None):
    """Caelus/OpenFOAM file writer

    Args:
        header (CaelusDict): The FoamFile entries

    Yields:
        printer (DictPrinter): A dictionary printer for printing data
    """
    fh = None
    try:
        fh = open(filename, 'w')
        fh.write(file_banner%{
            'timestamp': osutils.timestamp(),
            'version': version,
        })
        printer = DictPrinter(buf=fh)
        if header:
            printer.write_dict_item("FoamFile", header, True)
        fh.write(header_separator)
        yield printer
        fh.write(eof_separator)
    finally:
        if fh:
            fh.close()

class Indenter(object):
    """An indentation utility for use with DictPrinter"""

    def __init__(self, tab_width=4):
        """
        Args:
            tab_width (int): Default indentation width
        """
        #: Identation width
        self.tab_width = tab_width
        #: Current indentation column
        self.curr_indent = 0

    @property
    def indent_str(self):
        """Return an indentation string"""
        return ' '*self.curr_indent

    def emit(self, fh):
        """Emit the leading identation"""
        fh.write(self.indent_str)

    def indent(self):
        """Indent the tab"""
        self.curr_indent += self.tab_width

    def dedent(self):
        """Dedent the tab"""
        self.curr_indent -= self.tab_width

class DictPrinter(object):
    """Caelus Input File Pretty-printer

    Given a CaelusDict instance, this class will emit formatted data suitable
    for use with Caelus solvers
    """

    #: Default width for keywords
    keyword_fmt = "%-20s"

    no_keywd_values = (
        dtypes.Directive,
        dtypes.MacroSubstitution,
    )

    def __init__(self, buf=sys.stdout, tab_width=4):
        """
        Args:
            buf (file handle): A valid buffer to output to
            tab_width (int): Indentation width
        """
        self.indenter = Indenter(tab_width)
        self.buf = buf

    def __call__(self, entries):
        """Pretty-print the dictionary

        Args:
            entries (CaelusDict): Contents dictionary for output
        """
        if not entries:
            return
        tab_width = max(len(key) for key, value in entries.items()
                        if not isinstance(value, self.no_keywd_values))
        tab_width += self.indenter.tab_width
        curr_keywd_fmt = self.keyword_fmt
        self.keyword_fmt = "%%-%ds"%tab_width
        for key, value in entries.items():
            self.write_dict_item(key, value)
        self.keyword_fmt = curr_keywd_fmt

    def write_dict_item(self, key, value, nested=False):
        """Pretty-print a dictionary entry

        Args:
            key (str): Keyword for the parameter
            value (object): Value for the keyword
            nested (bool): Flag indicating whether the entries are nested
        """
        buf = self.buf
        indenter = self.indenter
        if isinstance(value, self.no_keywd_values):
            value.write_value(buf, indenter.indent_str)
        elif isinstance(value, dtypes.BoundaryList):
            buf.write("%d"%len(value.value))
            self.write_list(value.value)
        elif isinstance(value, dtypes.FoamType):
            buf.write(indenter.indent_str + self.keyword_fmt%key + " ")
            value.write_value(buf, indenter.indent_str)
        else:
            buf.write(indenter.indent_str + self.keyword_fmt%key + " ")
            self.write_value(value)

        if not nested:
            buf.write("\n")

    def write_value(self, value, recursive=False, indented=False):
        """Pretty-print an RHS entry based on its type

        Args:
            value (object): Value to be printed
            recursive (bool): Flag indicating whether the value is part of a
                              dictionary or a list
            indented (bool): Flag indicating whether value must be indented
        """
        buf = self.buf

        if isinstance(value, Mapping):
            self.write_dict(value)
        elif isinstance(value, np.ndarray):
            self.write_ndarray(value, recursive=recursive)
        elif isinstance(value, list):
            self.write_list(value, recursive=recursive)
        elif isinstance(value, bool):
            if indented:
                buf.write(self.indenter.indent_str)
            pvalue = "on" if value else "off"
            buf.write(pvalue)
            buf.write("\n" if recursive else ";\n")
        else:
            if indented:
                buf.write(self.indenter.indent_str)
            buf.write(np.str('' if value is None else value))
            buf.write("\n" if recursive else ";\n")

    def write_dict(self, value):
        """Pretty-print a Caelus dictionary type

        Args:
            value (Mapping): A valid python dict-like instance
        """
        buf = self.buf
        indenter = self.indenter
        curr_keywd_fmt = self.keyword_fmt
        tab_width = indenter.tab_width
        if value:
            tab_width = tab_width + max(
                len(key) for key in value.keys())
        self.keyword_fmt = "%%-%ds"%tab_width
        buf.write("\n" + indenter.indent_str + "{\n")
        indenter.indent()
        for key, val in value.items():
            self.write_dict_item(key, val, nested=True)
        indenter.dedent()
        buf.write(indenter.indent_str + "}\n\n")
        self.keyword_fmt = curr_keywd_fmt

    def write_ndarray(self, value, recursive=False):
        """Pretty-print a numeric list

        Args:
            value (np.ndarray): Array object
            recursive (bool): Flag indicating whether it is part of a list or dict
        """
        buf = self.buf
        indent = self.indenter.curr_indent
        indent_str = self.indenter.indent_str

        ndim = value.ndim
        arr_size = value.size
        arr_str = None
        # Ensure that numpy doesn't truncate the list
        threshold = np.get_printoptions()['threshold']
        try:
            np.set_printoptions(threshold=arr_size+10)
            arr_str = np.array_str(value, max_line_width=80-indent)
        finally:
            np.set_printoptions(threshold=threshold)

        # Replace brackets from numpy array to parenthesis for Caelus
        arr_str = re.sub(r']', ')', re.sub(r'\[', '(', arr_str))
        lines = arr_str.splitlines()
        num_lines = len(lines)
        if num_lines > 1:
            buf.write("\n" + indent_str + "(\n")
            indent_str += " "*self.indenter.tab_width
            buf.write(indent_str + lines[0][1:])
        elif ndim > 1:
            buf.write("\n" + indent_str + "(\n")
            indent_str += " "*self.indenter.tab_width
            buf.write(indent_str + lines[0][1:-1])
            buf.write("\n" + self.indenter.indent_str + ")")
        elif recursive:
            buf.write(indent_str + lines[0])
        else:
            buf.write(lines[0])
        for line in lines[1:-1]:
            if not line.strip():
                continue
            buf.write("\n")
            buf.write(indent_str + line[1:])
        if num_lines > 1:
            buf.write("\n" + indent_str + lines[-1][1:-1])
            indent_str = self.indenter.indent_str
            buf.write("\n" + indent_str + ")")
        buf.write("\n" if recursive else ";\n")

    def write_list(self, value, recursive=False):
        """Pretty-print a list entry

        Lists are mixed-type data entries. Empty lists and short string lists
        are printed flat in the same line. All other lists have their entries
        printed on new lines.

        Args:
            value (list): A list entry
            recursive (bool): Flag indicating whether this list is part of
                              another list or dict
        """
        buf = self.buf
        indenter = self.indenter

        # Empty list
        if not value:
            buf.write(" ()\n" if recursive else "\n(\n);\n")
            return

        # Short lists of strings
        if (len(value) <= 10 and all(isinstance(val, str) for val in value)):
            buf.write("( ")
            for val in value:
                buf.write(np.str(val)+ " " if val is not None else ' ')
            if recursive:
                buf.write(")")
            else:
                buf.write(");\n")
            return

        # General list object
        buf.write("\n" + indenter.indent_str + "(\n")
        indenter.indent()
        for val in value:
            if isinstance(val, Mapping) and len(val) == 1:
                for key, vvv in val.items():
                    self.write_dict_item(key, vvv, nested=True)
            else:
                self.write_value(val, True, indented=True)
        indenter.dedent()
        buf.write(indenter.indent_str + ")")
        buf.write("\n" if recursive else ";\n")
