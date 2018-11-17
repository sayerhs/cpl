# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods

"""
Caelus/OpenFOAM Input File Datatypes
"""

import sys
import abc
import re
import six
import numpy as np

@six.add_metaclass(abc.ABCMeta)
class FoamType(object):
    """Base class for a FOAM type"""

    @abc.abstractmethod
    def write_value(self, fh=sys.stdout, indent_str=''):
        """Write as a Caelus/OpenFOAM entry

        This method is called by :class:`~caelus.io.printer.DictPrinter` to
        format the data suitable for writing to a Caelus input file that can be
        read by the solvers.

        Args:
            fh (file): A valid file handle
            indent_str (str): Padding for indentation
        """

    def __repr__(self):
        return "<%s>"%self.__class__.__name__

class Dimension(FoamType):
    """Caelus dimensional units

    Represents the units of a dimensional quantity as an array of seven
    integers that represent the powers of the fundamental units: mass, length,
    time, temperature, quantity, current, and luminous intensity.
    """

    dim_names = "mass length time temperature quantity current luminous_intensity".split()

    def __init__(self, units=None, **kwargs):
        """Provide an array of individual units as keyword arguments

        Args:
            units (list): A list of 5 or 7 entries
        """
        self.units = np.zeros((7,), dtype=np.int)
        if units is None and not kwargs:
            raise RuntimeError("Either units or dimensional types must be provided")
        num_units = len(units)
        if units:
            if not ((num_units == 5) or (num_units == 7)):
                raise ValueError("Incorrect units specified: %s"%units)
            for i, uval in enumerate(units):
                self.units[i] = uval
        else:
            for i, key in enumerate(self.dim_names):
                if key in kwargs:
                    self.units[i] = kwargs[key]

    def write_value(self, fh=sys.stdout, indent_str=''):
        """Write out the dimensions

        Args:
            fh (file): A valid file handle
            indent_str (str): Padding for indentation
        """
        fh.write("[" + ' '.join("%d"%uval for uval in self.units) + "];\n")

    def __repr__(self):
        return "<%s: [%s]>"%(
            self.__class__.__name__,
            ' '.join('%d'%uval for uval in self.units))

class DimValue(FoamType):
    """A dimensioned value

    A dimensioned value contains three parts: the name, units, and the value.
    Units are of type :class:`Dimension` and value can be a scalar, vector,
    tensor or a symmetric tensor.
    """

    def __init__(self, name, dims, value):
        self.name = name
        self.dims = dims
        self.value = value

    def write_value(self, fh=sys.stdout, indent_str=''):
        """Write out the dimensional value"""
        fh.write("%s "%self.name)
        fh.write("[" + ' '.join("%d"%uval for uval in self.dims.units) + "] ")
        fh.write(np.str(self.value))
        fh.write(";\n")

    def __repr__(self):
        return "<%s: %s>"%(self.__class__.__name__, self.name)

class Directive(FoamType):
    """A Caelus directive type

    Directives are keyword-less entries that indicate certain processing
    actions and begin with a hash (``#``) symbol. For example, the
    ``#includeEtc`` directive that can be used to include files from
    ``foamEtc`` directory.
    """

    def __init__(self, directive, value):
        #: Type of directive (str)
        self.directive = directive
        #: Value of the directive (e.g., file to be included)
        self.value = value

    def write_value(self, fh=sys.stdout, indent_str=''):
        """Write out the dimensional value"""
        fh.write("\n%s %s\n"%(self.directive, self.value))

    def __repr__(self):
        return "<%s: %s>"%(self.__class__.__name__,
                           self.directive[1:])

class CalcDirective(FoamType):
    """A ``#calc`` directive entry

    Example::
        radHalfAngle    #calc "degToRad($halfAngle)";
    """

    def __init__(self, directive, value):
        self.directive = directive
        self.value = value

    def write_value(self, fh=sys.stdout, indent_str=''):
        """Write out the dimensional value"""
        fh.write("%s %s;\n"%(self.directive, self.value))

class CodeStream(FoamType):
    """A codestream entry

    Contains C++ code that can be compiled and executed to determine dictionary
    parameters.
    """

    def __init__(self, value):
        self.directive = "#codeStream"
        self.value = value

    def write_value(self, fh=sys.stdout, indent_str=''):
        """Write out the dimensional value"""
        fh.write("%s\n"%self.directive + indent_str + "{\n")
        indent_str += '    '
        indent_str1 = indent_str
        for ctype, value in self.value:
            fh.write(indent_str + ctype + "\n")
            lines = value.splitlines()
            nskip = lines[-1].count(' ')
            fh.write(indent_str + lines[0] + "\n")
            for line in lines[1:-1]:
                fh.write(indent_str1 + line[nskip:] + "\n")
            fh.write(indent_str + lines[-1].lstrip() + ";\n\n")
        fh.write("};\n")

class MacroSubstitution(FoamType):
    """Macro substition without keyword"""

    def __init__(self, value):
        self.value = value

    def write_value(self, fh=sys.stdout, indent_str=''):
        """Write standalone macro substitution"""
        fh.write(indent_str + "%s;\n"%self.value)

class Field(FoamType):
    """A field declaration

    This class represents both uniform and non-uniform fields. The attribute
    ``ftype`` indicates the type of field and the ``value`` contains the value
    for the given field. Uniform fields can be scalar, vector, tensor, or
    symmetric tensors. Non-uniform fields are typically a :class:`ListTemplate`
    entity.
    """

    def __init__(self, ftype, value):
        self.ftype = ftype
        self.value = value

    def write_uniform(self, fh=sys.stdout):
        """Write a uniform field"""
        fh.write(self.ftype)
        if isinstance(self.value, np.ndarray):
            fh.write(" (" + ' '.join(np.str(fval) for fval in self.value)
                     + ");\n")
        else:
            fh.write(" " + np.str(self.value) + ";\n")

    def write_nonuniform(self, fh=sys.stdout):
        """Write a non-uniform field"""
        if isinstance(self.value, ListTemplate):
            self.value.write_value(fh)
        else:
            arr_size = self.value.size
            arr_len = len(self.value)
            arr_str = None
            threshold = np.get_printoptions()['threshold']
            try:
                np.set_printoptions(threshold=arr_size+10)
                arr_str = np.array_str(self.value, max_line_width=80)
            finally:
                np.set_printoptions(threshold=threshold)
            arr_str = re.sub(r']', ')', re.sub(r'\[', '(', arr_str))
            fh.write("\n%d\n"%arr_len)
            fh.write(arr_str + ";\n")

    def write_value(self, fh=sys.stdout, indent_str=''):
        """Write value in OpenFOAM format"""
        if self.ftype == "uniform":
            self.write_uniform(fh)
        else:
            self.write_nonuniform(fh)

    def __repr__(self):
        return "<%s: %s>"%(self.__class__.__name__,
                           self.ftype)

class BoundaryList(FoamType):
    """polyMesh/boundary file"""

    def __init__(self, value):
        self.value = value

    def write_value(self, fh=sys.stdout, indent_str=''):
        fh.write("\n" + indent_str + "%d"%len(self.value))

class MultipleValues(FoamType):
    """Multiple values for single keyword

    Example::
        laplacian(nuEff,U)       Gauss linear corrected;

    Here "Gauss linear corrected" is stored as an instance of this class to
    disambiguate between multi-valued entries and plain lists.
    """

    def __init__(self, value):
        self.value = value

    def write_value(self, fh=sys.stdout, indent_str=''):
        fh.write(" ".join(np.str(val) for val in self.value))
        fh.write(";\n")

    def __repr__(self):
        return "<MultipleValues: %s>"%self.value

    def __str__(self):
        return " ".join(np.str(val) for val in self.value)

class ListTemplate(FoamType):
    """List<T> type entries"""

    def __init__(self, ltype, value):
        self.list_type = ltype
        self.value = value

    def write_value(self, fh=sys.stdout, indent_str=''):
        """Write out a List<T> value"""
        arr_size = self.value.size
        arr_len = len(self.value)
        arr_str = None
        threshold = np.get_printoptions()['threshold']
        try:
            np.set_printoptions(threshold=arr_size+10)
            arr_str = np.array_str(self.value, max_line_width=80)
        finally:
            np.set_printoptions(threshold=threshold)
        arr_str = re.sub(r']', ')', re.sub(r'\[', '(', arr_str))
        fh.write("\n%s %d\n"%(self.list_type, arr_len))
        fh.write(arr_str + ";\n")
