# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import pytest

def assert_token_types(clex, text, types):
    """Assert expected token types for a given input text"""
    lex_types = [i.type for i in clex.token_stream(text)]
    assert len(lex_types) == len(types)
    for inp, out in zip(types, lex_types):
        assert inp == out

def test_token_position(clex):
    inp = "text1\n\n    text2\n    text3 { abc def; }\n"
    tokens = list(clex.token_stream(inp))
    assert(len(tokens) == 8)
    linenos = [1, 3, 4, 4, 4, 4, 4, 4]
    for tok, lval in zip(tokens, linenos):
        assert(tok.lineno == lval)

def test_keywords(clex):
    inp = "dimensions uniform nonuniform"
    etypes = inp.upper().split()
    assert_token_types(clex, inp, etypes)

def test_directives(clex):
    text = "#include #includeEtc #includeIfPresent #includeFunc #inputMode"
    etypes = ['DIRECTIVES']*5
    assert_token_types(clex, text, etypes)

def test_codestream(clex):
    text = "#codeStream \n{ code #{ double value = 0.0 #} }"
    etypes = "CODESTREAM LBRACE ID CODE_BLOCK RBRACE".split()
    assert_token_types(clex, text, etypes)

def test_identifiers(clex):
    text = 'startTime endTime div(phi,U) grad(p) fvSolution'
    assert_token_types(clex, text, ['ID']*5)

def test_macrovars(clex):
    text = '$initialPressure'
    assert_token_types(clex, text, ['MACRO_VAR'])

def test_ints(clex):
    text = "-1 1 0 8192 42"
    assert_token_types(clex, text, ['INT_CONST']*5)

def test_floats(clex):
    text = "3.1415926 1.01e+12 +1.012 -1.012 -1.01e-12"
    assert_token_types(clex, text, ['FLOAT_CONST']*5)

def test_string_literals(clex):
    text = '"this is a string literal" "(U|T|k|epsilon|omega)" "(SIMPLE|SIMPLEC)"'
    assert_token_types(clex, text, ['STRING_LITERAL']*3)

def test_simple_comment(clex):
    text = """// comment line 1
    // comment line 2
    startTime 0;
    endTime   $endTime;
    """
    etypes = "ID INT_CONST SEMI ID MACRO_VAR SEMI".split()
    assert_token_types(clex, text, etypes)

def test_multiline_comment(clex):
    text = """
    startTime   0;
    /* Multi line comment begins here
       Line 2
       Line 3
    */
    endTime   100;
    """
    tokens = list(clex.token_stream(text))
    assert(len(tokens) == 6)
    assert(tokens[0].lineno == 2)
    assert(tokens[0].value == "startTime")

def test_unmatched_comment(clex):
    text = """
    startTime   0;
    /* Multi line comment begins here
       Line 2
       Line 3
    endTime   100;
    """
    with pytest.raises(SyntaxError):
        list(clex.token_stream(text))

def test_unmatched_quote(clex):
    text = '''"this is an unmatched '''
    with pytest.raises(SyntaxError):
        list(clex.token_stream(text))

def test_unmatched_codeblock(clex):
    text = """
    #{
        double time = 0.0;
        double end_time = time + 1000.0;
    """
    with pytest.raises(SyntaxError):
        list(clex.token_stream(text))
