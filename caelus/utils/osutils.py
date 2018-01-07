# -*- coding: utf-8 -*-

"""\
Miscellaneous OS utilities

"""

import os
from contextlib import contextmanager

def ostype():
    """String indicating the operating system type

    Returns:
        str: One of ["linux", "darwin", "windows"]
    """
    return ("windows" if os.name == 'nt' else
            os.uname()[0].lower())

def username():
    """Return the username of the current user"""
    import getpass
    return getpass.getuser()

def user_home_dir():
    """Return the absolute path of the user's home directory"""
    return os.path.expanduser("~")

def abspath(pname):
    """Return the absolute path of the directory.

    This function expands the user home directory as well as any shell
    variables found in the path provided and returns an absolute path.
    """
    pth1 = os.path.expanduser(pname)
    pth2 = os.path.expandvars(pth1)
    return os.path.abspath(pth2)

def ensure_directory(dname):
    """Check if directory exists, if not, create it.

    Args:
        dname (path): Directory name to check for

    Returns:
        Path: Absolute path to the directory
    """
    abs_dir = abspath(dname)
    if not os.path.exists(abs_dir):
        os.makedirs(abs_dir)
    return abs_dir

@contextmanager
def set_work_dir(dname, create=False):
    """A with-block to execute code in a given directory.

    Args:
        dname (path): Path to the working directory.
        create (bool): If true, directory is created prior to execution

    Returns:
        path: Absolute path to the execution directory
    """
    abs_dir = abspath(dname)
    if create:
        ensure_directory(abs_dir)

    orig_dir = os.getcwd()
    try:
        os.chdir(abs_dir)
        yield abs_dir
    finally:
        os.chdir(orig_dir)
