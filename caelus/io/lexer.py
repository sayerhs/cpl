# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, no-self-use, bad-whitespace, missing-docstring

"""\
PLY Lexer for Caelus Input Files
--------------------------------

This module implements the lexer (:ref:`CaelusLexer`) that generates tokens
used by (:ref:`~caelus.io.parser.CaelusParser`) to process the Caelus input
file grammar.
"""

# The code here is inspired by Eli Bendersky's excellent pycparser utility on
# Github. See the repository for details:
# https://github.com/eliben/pycparser/blob/master/pycparser/c_lexer.py

from ply import lex
from ply.lex import TOKEN

class CaelusLexer(object):
    """Lexer for Caelus and OpenFOAM file formats"""

    def __init__(self, error_func, **kwargs):
        """Create a new lexer instance

        Args:
            error_func (func): A function that takes three arguments (error
                message, line number, and column number) that will be called if
                an error is encountered while processing the input.
        """
        #: Function invoked when the lexer encounters an error while processing
        #: the input
        self.error_func = error_func
        #: The filename from which input is being processed
        self.filename = '<input>'
        self.lexer = lex.lex(module=self, **kwargs)
        self.last_token = None

    def input(self, text):
        """Wrapper method to lexer.input"""
        self.lexer.input(text)

    def token(self):
        """Return a token from the input stream"""
        self.last_token = self.lexer.token()
        return self.last_token

    def reset_lineno(self):
        """Reset line number for parsing"""
        self.lexer.lineno = 1

    def get_token_position(self, tok): # pylint: disable=no-self-use
        """Return the current column position"""
        col = (tok.lexpos - tok.lexer.lexdata.rfind(
            '\n', 0, tok.lexpos))
        return (tok.lineno, col)

    ###
    ### Lexer implementation
    ###

    # Keywords encountered within input files
    keywords = ('DIMENSIONS', 'UNIFORM', 'NONUNIFORM', 'LIST')

    # Keywords are matched by the identifier, so we will intercept it and
    # change token type appropriately
    keyword_map = {k.lower(): k for k in keywords}

    tokens = keywords + (
        'ID', 'MACRO_VAR', 'DIRECTIVES', 'CODE_BLOCK', 'CODESTREAM', 'CALC',

        # Constants and literals
        'INT_CONST', 'FLOAT_CONST', 'CHAR_CONST', 'STRING_LITERAL',

        # Delimeters
        'LPAREN', 'RPAREN',     # ( )
        'LBRACKET', 'RBRACKET', # [ ]
        'LBRACE', 'RBRACE',     # { }
        'SEMI',
        # 'COLON',        # ; :
        # 'LT', 'GT',             # < >
        # 'COMMA', 'PERIOD',      # . ,
    )

    # Accepted variable names in Caelus/OpenFOAM
    identifier = r'[a-zA-Z_]([^ ";/\{\}\t\n])*'
    # Macro variable
    mvar1 = r'\$' + identifier
    mvar2 = r'\${[^ ";\n\t/]+}'
    mvar3 = r'\$[.:][^ ";\n\t]+'
    macro_var = r'(' + mvar1 + r'|' + mvar2 + r'|' + mvar3 + r')'
    #macro_var = r'[$][a-zA-Z0-9_]+'
    # Function entry
    directives = r'[#][a-zA-Z0-9_]+'

    # Numerical constants
    integer_suffix_opt = r'(([uU]ll)|([uU]LL)|(ll[uU]?)|(LL[uU]?)|([uU][lL])|([lL][uU]?)|[uU])?'
    decimal_constant = r'([-+]?(' + '(0'+integer_suffix_opt+')|([1-9][0-9]*'+integer_suffix_opt+')))'


    exponent_part = r"""([eE][-+]?[0-9]+)"""
    fractional_constant = r"""([-+]?[0-9]*\.[0-9]+)|([0-9]+\.)"""
    floating_constant = ('(((('+fractional_constant+')' +
                         exponent_part + '?)|([0-9]+' +
                         exponent_part + '))[FfLl]?)')

    simple_escape = r"""([a-zA-Z._~!=&\^\-\\?'"])"""
    decimal_escape = r"""(\d+)"""
    hex_escape = r"""(x[0-9a-fA-F]+)"""
    bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-7])"""

    escape_sequence = r"""(\\("""+simple_escape+'|'+decimal_escape+'|'+hex_escape+'))'
    cconst_char = r"""([^'\\\n]|"""+escape_sequence+')'
    char_const = "'"+cconst_char+"'"
    unmatched_quote = "('"+cconst_char+"*\\n)|('"+cconst_char+"*$)"
    bad_char_const = r"""('"""+cconst_char+"""[^'\n]+')|('')|('"""+bad_escape+r"""[^'\n]*')"""

    # string literals (K&R2: A.2.6)
    string_char = r"""([^"\\\n]|"""+escape_sequence+')'
    string_literal = '"'+string_char+'*"'
    bad_string_literal = '"'+string_char+'*?'+bad_escape+string_char+'*"'

    # Ignore spaces and tabs
    t_ignore = ' \t'

    def t_NEWLINE(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")

    def t_COMMENT(self, t):
        r'/[*/]'
        tlex = t.lexer
        is_multi = False
        com_end = -1
        if t.value[-1] == '*': # Multi-line comment
            is_multi = True
            com_end = tlex.lexdata.find("*/", tlex.lexpos)
        else:
            com_end = tlex.lexdata.find("\n", tlex.lexpos)

        if com_end < 0:
            # We reached the end of input without encountering comment end
            # characters. So adjust the lexer locations to indicate end of
            # parse or error.
            tlex.lexpos = len(tlex.lexdata)
            com_end = len(tlex.lexdata)
            if is_multi:
                self._error("Unmatched multi-line comment", t)
        else:
            com_end += 2 if is_multi else 1
            tlex.lexpos = com_end

        comment_str = tlex.lexdata[t.lexpos:com_end]
        num_lines = comment_str.count('\n')
        tlex.lineno += num_lines

    def t_CODE_BLOCK(self, t):
        r'\#\{'
        tlex = t.lexer
        code_end = tlex.lexdata.find("#}", tlex.lexpos)
        if code_end < 0:
            tlex.lexpos = len(tlex.lexdata)
            code_end = len(tlex.lexdata)
            self._error("Unmatched code block", t)
        else:
            code_end += 2
            tlex.lexpos = code_end

        t.value = tlex.lexdata[t.lexpos:code_end]
        num_lines = t.value.count('\n')
        tlex.lineno += num_lines
        return t


    # Delimiters
    t_LPAREN   = r'\('
    t_RPAREN   = r'\)'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_LBRACE   = r'\{'
    t_RBRACE   = r'\}'
    t_SEMI     = r';'
    # t_LT       = r'<'
    # t_GT       = r'>'
    # t_COMMA    = r','
    # t_PERIOD   = r'\.'
    # t_COLON    = r':'

    t_STRING_LITERAL = string_literal

    @TOKEN(floating_constant)
    def t_FLOAT_CONST(self, t):
        t.value = float(t.value)
        return t

    @TOKEN(decimal_constant)
    def t_INT_CONST(self, t):
        t.value = int(t.value)
        return t

    @TOKEN(char_const)
    def t_CHAR_CONST(self, t):
        return t

    @TOKEN(unmatched_quote)
    def t_UNMATCHED_QUOTE(self, t):
        msg = "Unmatched '"
        self._error(msg, t)

    @TOKEN(bad_char_const)
    def t_BAD_CHAR_CONST(self, t):
        msg = "Invalid char constant %s" % t.value
        self._error(msg, t)

    @TOKEN(bad_string_literal)
    def t_BAD_STRING_LITERAL(self, t):
        msg = "String contains invalid escape code"
        self._error(msg, t)

    def t_LIST(self, t):
        "List<[A-Za-z]+>"
        return t

    @TOKEN(macro_var)
    def t_MACRO_VAR(self, t):
        return t

    @TOKEN(directives)
    def t_DIRECTIVES(self, t):
        if t.value[1:] == "codeStream":
            t.type = "CODESTREAM"
        elif t.value[1:] == "calc":
            t.type = "CALC"
        return t

    @TOKEN(identifier)
    def t_ID(self, t):
        t.type = self.keyword_map.get(t.value.lower(), "ID")
        return t

    def t_error(self, tok):
        """Create an error message"""
        msg = "Illegal character %s"%(repr(tok.value))
        self._error(msg, tok)

    def _error(self, msg, tok):
        lineno, col = self.get_token_position(tok)
        self.error_func(msg, lineno, col)

    def token_stream(self, text):
        """Generate a stream of tokens from the text"""
        self.input(text)
        return iter(self.token, None)
