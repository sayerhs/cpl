# -*- coding: utf-8 -*-

"""\
Miscellaneous OS utilities

"""

import os
import fnmatch
import shutil
import logging
from contextlib import contextmanager

_lgr = logging.getLogger(__name__)

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
        _lgr.debug("Setting work directory: %s", abs_dir)
        yield abs_dir
    finally:
        os.chdir(orig_dir)
        _lgr.debug("Setting work directory: %s", abs_dir)

def clean_directory(dirname,
                    preserve_patterns=None):
    """Utility function to remove files and directories from a given directory.

    User can specify a list of filename patterns to preserve with the
    ``preserve_patterns`` argument. These patterns can contain shell wildcards
    to glob multiple files.

    Args:
        dirname (path): Absolute path to the directory whose entries are purged.
        preserve_patterns (list): A list of shell wildcard patterns
    """
    _lgr.debug("Removing files in directory: %s", dirname)
    ppatterns = preserve_patterns or []
    with set_work_dir(dirname) as wdir:
        for fpath in os.listdir(wdir):
            is_preserve = False
            for pp in ppatterns:
                if fnmatch.fnmatch(fpath, pp):
                    is_preserve = True
                    break
            if is_preserve:
                continue

            if os.path.isdir(fpath):
                shutil.rmtree(fpath)
            elif os.path.isfile(fpath) or os.path.islink(fpath):
                os.remove(fpath)
