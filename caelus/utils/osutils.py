# -*- coding: utf-8 -*-

"""\
Miscellaneous utilities
-----------------------

This module implements functions that are utilized throughout CPL. They mostly
provide a higher-level interface to various ``os.path`` functions to make it
easier to perform some tasks.

.. autosummary::
   :nosignatures:

   set_work_dir
   ensure_directory
   abspath
   ostype
   timestamp
"""

import os
import fnmatch
import shutil
import logging
from datetime import datetime
from contextlib import contextmanager
import pytz

_lgr = logging.getLogger(__name__)

def ostype():
    """String indicating the operating system type

    Returns:
        str: One of ["linux", "darwin", "windows"]
    """
    return ("windows" if os.name == 'nt' else
            os.uname()[0].lower())

def timestamp(time_format=None, time_zone=pytz.utc):
    """Return a formatted timestamp for embedding in files

    Args:
        time_format: A time formatter suitable for strftime
        time_zone: Time zone used to generate timestamp (Default: UTC)

    Returns:
        str: A formatted time string
    """
    time_fmt = time_format or "%Y-%m-%d %H:%M:%S (%Z)"
    return datetime.now(time_zone).strftime(time_fmt)

def backup_file(fname, time_format=None, time_zone=pytz.utc):
    """Given a filename return a timestamp based backup filename

    Args:
        time_format: A time formatter suitable for strftime
        time_zone: Time zone used to generate timestamp (Default: UTC)

    Returns:
        str: A timestamped filename suitable for creating backups
    """
    bname = os.path.basename(fname)
    name, ext = os.path.splitext(bname)
    time_fmt = time_format or "%Y%m%d-%H%M%S-%Z"
    tstamp = datetime.now(time_zone).strftime(time_fmt)
    bak_name = name + "_" + tstamp + ext
    return os.path.join(os.path.dirname(fname), bak_name)

def username():
    """Return the username of the current user"""
    import getpass
    return getpass.getuser()

def user_home_dir():
    """Return the absolute path of the user's home directory"""
    try:
        path = os.path.expanduser("~")
    except ImportError:
        pass
    else:
        if os.path.isdir(path):
            return path

    for envvar in "HOME USERPROFILE".split():
        path = os.environ.get(envvar)
        if path is not None and os.path.isdir(path):
            return path
    return None


def abspath(pname):
    """Return the absolute path of the directory.

    This function expands the user home directory as well as any shell
    variables found in the path provided and returns an absolute path.

    Args:
        pname (path): Pathname to be expanded

    Returns:
        path: Absolute path after all substitutions
    """
    pth1 = os.path.expanduser(pname)
    pth2 = os.path.expandvars(pth1)
    return os.path.normpath(os.path.abspath(pth2))

def path_exists(pname):
    """Check path of the directory exists.

    This function expands the user home directory as well as any shell
    variables found in the path provided and checks if that path exists.

    Args:
        pname (path): Pathname to be checked

    Returns:
        bool: True if path exists
    """
    return os.path.exists(abspath(pname))

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

    Example:
        >>> with osutils.set_work_dir("results_dir", create=True) as wdir:
        ...     with open(os.path.join(wdir, "results.dat"), 'w') as fh:
        ...         fh.write("Data")
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

def remove_files_dirs(paths, basedir=None):
    """Remove files and/or directories

    Args:
        paths (list): A list of file paths to delete (no patterns allowed)
        basedir (path): Base directory to search
    """
    wdir = basedir or os.getcwd()
    with set_work_dir(wdir):
        for fpath in paths:
            if os.path.exists(fpath):
                if os.path.isdir(fpath):
                    shutil.rmtree(fpath)
                elif os.path.isfile(fpath) or os.path.islink(fpath):
                    os.remove(fpath)

def copy_tree(srcdir, destdir, symlinks=False, ignore_func=None):
    """Enchanced version of shutil.copytree

       - removes the output directory if it already exists.

    Args:
        srcdir (path): path to source directory to be copied.
        destdir (path): path (or new name) of destination directory.
        symlinks (bool): as in shutil.copytree
        ignore_func (func): as in shutil.copytree
    """
    if os.path.exists(destdir):
        shutil.rmtree(destdir)
    shutil.copytree(srcdir, destdir, symlinks, ignore_func)

def split_path(fname):
    """Split a path into directory, basename, extension

    Returns:
        tuple: (directory, basename, extension)
    """
    abs_fname = abspath(fname)
    fdir = os.path.dirname(abs_fname)
    ftmp = os.path.basename(abs_fname)
    base, ext = os.path.splitext(ftmp)
    return (fdir, base, ext)
