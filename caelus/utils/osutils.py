# -*- coding: utf-8 -*-

"""\
Miscellaneous OS utilities

"""

import os

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
