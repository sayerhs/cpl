# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import pytest
import six

from caelus.io.lexer import CaelusLexer
from caelus.io.parser import CaelusParser
from caelus.io.printer import DictPrinter


@pytest.fixture
def clex():
    def error_func(msg, lineno, col):
        mstr = "{msg} [<input>:{lineno}:{col}]".format(
            msg=msg, lineno=lineno, col=col
        )
        raise SyntaxError(mstr)

    clex = CaelusLexer(error_func=error_func, optimize=False)
    return clex


@pytest.fixture
def cparse():
    return CaelusParser(lex_optimize=False, yacc_optimize=False)


@pytest.fixture
def cprinter():
    buf = six.StringIO()
    return DictPrinter(buf=buf)
