# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,too-many-arguments,no-self-use,too-many-public-methods,line-too-long

"""\
Caelus/OpenFOAM File Parser
---------------------------

This module contains the implementation of the PLY YACC parser
(:ref:`CaelusParseError`) and a custom exception (:ref:`CaelusParseError`) that
is used to indicate syntax errors encountered when parsing input files.

"""

# The code here is inspired by Eli Bendersky's excellent pycparser utility on
# Github. See the repository for details:
# https://github.com/eliben/pycparser/blob/master/pycparser/c_parser.py

from ply import yacc
import numpy as np
from .lexer import CaelusLexer
from . import caelusdict as cdict
from . import dtypes

class CaelusParseError(Exception):
    """Custom error class for parser errors"""

class CaelusParser(object):
    """Implementation of PLY YACC parser for input files"""

    def __init__(self,
                 lexer=CaelusLexer,
                 lex_optimize=True,
                 lextab='caelus.io.caeluslextab',
                 yacc_optimize=True,
                 yacctab='caelus.io.caelusyacctab',
                 yacc_debug=False,
                 taboutputdir=None,
                 dict_type=cdict.CaelusDict):
        """
        Args:
            lex_optimize (bool): Save Lexer table instead of regenerating
            lextab (str): Generated lex table
            yacc_optimize (bool): Save parser table
            yacctab (str): Generated parser table
            yacc_debug (bool): Generate parser.out file
            taboutputdir (path): Path where files are output
            dict_type (Struct): Dictionary type to store parsed values
        """
        #: Lexer instance of Caelus input file tokens
        self.clex = lexer(error_func=self._lex_error_func,
                          optimize=lex_optimize,
                          lextab=lextab,
                          outputdir=taboutputdir)
        #: Tokens generated by the lexer
        self.tokens = self.clex.tokens
        #: The PLY YACC parser instance
        self.cparser = yacc.yacc(
            module=self, optimize=yacc_optimize,
            tabmodule=yacctab, debug=yacc_debug,
            outputdir=taboutputdir)
        self._dict_type = dict_type

        #: Internal counter to track the directives encountered so far. This is
        #: used to generate unique keys for the directives for storing in the
        #: CaelusDict instance returned by the parse method.
        self.directive_counter = 0
        #: Internal counter used to track standalone macro expansions.
        self.macro_counter = 0

    def parse(self, text, filename='<input>', debuglevel=0):
        """Parse a text block based on Caelus/OpenFOAM grammar

        Args:
            text (str): The text to be parsed
            filename (path): Filename used in error messages
            debuglevel (int): Verbosity of PLY messages

        Returns:
            CaelusDict: The parsed file as a dictionary
        """
        self.clex.filename = filename
        self.clex.reset_lineno()
        productions = self.cparser.parse(
            input=text, lexer=self.clex.lexer, debug=debuglevel)
        return self._dict_type(productions)

    def _parse_error(self, msg, p=None):
        """Parser error message handler

        Args:
            msg (str): The error message
            p (ply): The YACC variable
        """
        filename = self.clex.filename
        if p:
            lineno, col = self.clex.get_token_position(p)
        else:
            lineno, col = self.clex.lexer.lineno, "EOF"
        mstr = "{msg} [{filename}:{lineno}:{col}]".format(
            msg=msg, filename=filename, lineno=lineno, col=col)
        raise CaelusParseError(mstr)

    def _lex_error_func(self, msg, lineno, col):
        """Function for lex error messages

        Args:
            msg (str): The error message
            lineno (int): The line number where error was encountered
            col (int): The column of the token being parsed
        """
        filename = self.clex.filename
        mstr = "{msg} [{filename}:{lineno}:{col}]".format(
            msg=msg, filename=filename, lineno=lineno, col=col)
        raise CaelusParseError(mstr)

    ##### Caleus input file grammar RULES #####

    def p_foam_file(self, p):
        """ foam_file : dict_items
                      | empty
        """
        if p[1]:
            p[0] = p[1]
        else:
            p[0] = []

    def p_dict_items(self, p):
        """ dict_items : dict_items dict_entry
                       | dict_entry
        """
        p[0] = [p[1]] if (len(p) == 2) else p[1] + [p[2]]

    def p_boundary_list(self, p):
        """ dict_entry : numbered_list"""
        p[0] = ("boundary", dtypes.BoundaryList(p[1]))

    def p_simple_dict(self, p):
        """ simple_dict : LBRACE empty RBRACE
                        | LBRACE dict_items RBRACE
                        | LBRACE dict_items RBRACE SEMI
        """
        p[0] = self._dict_type(p[2]) if p[2] else self._dict_type([])

    def p_dict_entry(self, p):
        """ dict_entry : identifier rhs_value SEMI
                       | identifier simple_list SEMI
                       | identifier numbered_list SEMI
                       | identifier tokid_list SEMI
                       | identifier empty SEMI
                       | identifier UNIFORM SEMI
                       | DIMENSIONS dimension SEMI
                       | identifier simple_dict
        """
        p[0] = (p[1], p[2])

    def p_dict_entry1(self, p):
        """ dict_entry : directive """
        key = "directive_%03d"%self.directive_counter
        self.directive_counter += 1
        p[0] = (key, p[1])

    def p_dict_entry2(self, p):
        """ dict_entry : MACRO_VAR SEMI
                       | MACRO_VAR
        """
        key = "macro_%03d"%self.macro_counter
        self.macro_counter += 1
        p[0] = (key, dtypes.MacroSubstitution(
            p[1], len(p) > 2))

    def p_dict_entry3(self, p):
        """ dict_entry : code_stmt """
        p[0] = p[1]

    def p_uniform_field(self, p):
        """ dict_entry    : identifier UNIFORM number SEMI
                          | identifier UNIFORM vector SEMI
                          | identifier UNIFORM tensor SEMI
                          | identifier UNIFORM symm_tensor SEMI
                          | identifier UNIFORM MACRO_VAR SEMI
        """
        p[0] = (p[1], dtypes.Field("uniform", p[3]))

    def p_nonuniform_field(self, p):
        """ dict_entry : identifier NONUNIFORM tokid_list SEMI
                       | identifier NONUNIFORM numbered_list SEMI
        """
        p[0] = (p[1], dtypes.Field("nonuniform", p[3]))

    def p_multi_list1(self, p):
        """ dict_entry : identifier identifier simple_list SEMI
                       | identifier simple_list simple_list SEMI
                       | identifier simple_list identifier simple_list SEMI
        """
        p[0] = (p[1], dtypes.MultipleValues(p[2:-1]))

    def p_simple_list(self, p):
        """ simple_list : LPAREN empty RPAREN
                        | LPAREN list_items RPAREN
        """
        # p[0] = p[2] if p[2] else []
        if p[2]:
            try:
                if all(isinstance(ii, int) for ii in p[2]):
                    p[0] = np.asarray(p[2], dtype=np.int_)
                elif all(isinstance(ii, np.ndarray) for ii in p[2]):
                    p[0] = np.asarray(p[2])
                # elif all(isinstance(ii, list) for ii in p[2]):
                #     print(p[2])
                #     p[0] = np.asarray(p[2])
                else:
                    p[0] = np.asarray(p[2], dtype=np.float_)
            except (ValueError, TypeError):
                p[0] = p[2]
        else:
            p[0] = []

    def p_numbered_list(self, p):
        """ numbered_list : INT_CONST LPAREN list_items RPAREN"""
        try:
            if all(isinstance(ii, int) for ii in p[3]):
                p[0] = np.asarray(p[3], dtype=np.int_)
            elif all(isinstance(ii, (np.ndarray, list)) for ii in p[3]):
                p[0] = np.asarray(p[3])
            else:
                p[0] = np.asarray(p[3], dtype=np.float_)
        except (ValueError, TypeError):
            p[0] = p[3]

    def p_tokid_list(self, p):
        """ tokid_list : LIST simple_list
                       | LIST numbered_list
        """
        try:
            if all(isinstance(ii, int) for ii in p[2]):
                p[0] = dtypes.ListTemplate(
                    p[1], np.asarray(p[2], dtype=np.int_))
            elif all(isinstance(ii, (np.ndarray, list)) for ii in p[2]):
                p[0] = dtypes.ListTemplate(
                    p[1], np.asarray(p[2]))
            else:
                p[0] = dtypes.ListTemplate(
                    p[1], np.asarray(p[2], dtype=np.float_))
        except (ValueError, TypeError):
            p[0] = dtypes.ListTemplate(p[1], p[2])

    def p_list_items(self, p):
        """ list_items : list_items list_item
                       | list_item
        """
        p[0] = [p[1]] if (len(p) == 2) else p[1] + [p[2]]

    def p_list_item(self, p):
        """ list_item : value
                      | simple_list
                      | identifier simple_dict
                      | directive
        """
        if len(p) == 3:
            p[0] = self._dict_type([(p[1], p[2])])
        else:
            p[0] = p[1]

    def p_face_list(self, p):
        """ dict_entry : INT_CONST LPAREN face_list_items RPAREN """
        p[0] = ("face_list", np.array(p[3], dtype=np.int_))

    def p_face_list_items(self, p):
        """ face_list_items : face_list_items int_list
                            | int_list
        """
        p[0] = [p[1]] if (len(p) == 2) else p[1] + [p[2]]

    def p_int_list(self, p):
        """ int_list : number LPAREN int_list_items RPAREN"""
        p[0] = np.array(p[3], dtype=int)

    def p_int_list_items(self, p):
        """ int_list_items : INT_CONST int_list_items
                           | empty
        """
        if len(p) == 2:
            p[0] = []
        else:
            p[0] = [p[1]] + p[2]

    def p_rhs_value(self, p):
        """ rhs_value : value rhs_value_opt
        """
        if len(p) == 2 or not p[2]:
            p[0] = p[1]
        else:
            p[0] = dtypes.MultipleValues([p[1]] + p[2])

    def p_rhs_value_opt(self, p):
        """ rhs_value_opt : rhs_value_opt value
                          | rhs_value_opt simple_dict
                          | empty
        """
        p[0] = [] if (len(p) == 2) else p[1] + [p[2]]

    def p_value(self, p):
        """ value : identifier
                  | number
                  | dim_value
                  | codestream
                  | calc
                  | eval
                  | MACRO_VAR
                  | CHAR_CONST
        """
        p[0] = p[1]

    def p_codestream(self, p):
        """ codestream : CODESTREAM LBRACE codestream_value RBRACE"""
        p[0] = dtypes.CodeStream(p[3])

    def p_codestream_value(self, p):
        """ codestream_value : code_stmt
                             | codestream_value code_stmt
        """
        p[0] = [p[1]] if (len(p) == 2) else p[1] + [p[2]]

    def p_code_stmt(self, p):
        """ code_stmt : identifier CODE_BLOCK SEMI """
        p[0] = (p[1], p[2])

    def p_directive(self, p):
        """ directive : DIRECTIVES identifier """
        p[0] = dtypes.Directive(p[1], p[2])

    def p_calc(self, p):
        """ calc : CALC STRING_LITERAL"""
        p[0] = dtypes.CalcDirective(p[1], p[2])

    def p_eval(self, p):
        """ eval : EVAL CODE_BLOCK
                 | EVAL STRING_LITERAL
        """
        p[0] = dtypes.EvalDirective(p[1], p[2])

    def p_dim_value(self, p):
        """ dim_value : identifier dimension number
                      | identifier dimension vector
                      | identifier dimension symm_tensor
                      | identifier dimension tensor
        """
        p[0] = dtypes.DimValue(p[1], p[2], p[3])

    def p_dimension(self, p):
        """ dimension : LBRACKET INT_CONST INT_CONST INT_CONST INT_CONST INT_CONST INT_CONST INT_CONST RBRACKET
                      | LBRACKET INT_CONST INT_CONST INT_CONST INT_CONST INT_CONST RBRACKET
        """
        p[0] = dtypes.Dimension(p[2:-1])

    def p_dimension_str(self, p):
        """ dimension : LBRACKET identifier RBRACKET """
        p[0] = dtypes.DimStr(p[2])

    def p_vector(self, p):
        """ vector : LPAREN number number number RPAREN"""
        p[0] = np.array(p[2:5])

    def p_symm_tensor(self, p):
        """ symm_tensor : LPAREN number number number number number number RPAREN """
        p[0] = np.array(p[2:7])

    def p_tensor(self, p):
        """ tensor : LPAREN number number number number number number number number number RPAREN """
        p[0] = np.array(p[2:10])

    def p_number(self, p):
        """ number : INT_CONST
                   | FLOAT_CONST
        """
        p[0] = p[1]

    def p_identifier(self, p):
        """ identifier : ID
                       | STRING_LITERAL
        """
        p[0] = p[1]

    def p_empty(self, p):
        """ empty : """

    def p_error(self, p):
        """Error generator"""
        if p:
            self._parse_error("Before: %s"%p.value, p)
        else:
            self._parse_error("Premature end of input", p)
