# -*- coding: utf-8 -*-

"""\
Test running python utility
"""

import pytest
from caelus.utils import pyutils

script_contents = """

def func1():
    "Test1"
    return "func1"


def func2():
    "Test1"
    return "func2"
"""

def test_imports(tmpdir):
    """Test whether we can import a script."""
    pyfile = tmpdir / "caelus-script-import.py"
    with open(pyfile, 'w') as fh:
        fh.write(script_contents)
    pymod = pyutils.import_script(pyfile)
    assert hasattr(pymod, "func1")
    assert hasattr(pymod, "func2")

def test_noscript(tmpdir):
    """Test non-existence of file"""
    with pytest.raises(FileNotFoundError):
        pyutils.import_script(tmpdir / "non-existent.py")
