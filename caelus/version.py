# -*- coding: utf-8 -*-

"""\
CPL Version
"""

import os
import subprocess
import shlex

_basic_version = "v2.0.0"

def git_describe():
    """Get version from git-describe"""
    dirname = os.path.dirname(__file__)
    cwd = os.getcwd()
    git_ver = _basic_version
    try:
        os.chdir(dirname)
        cmdline = "git describe --tags --dirty"
        cmd = shlex.split(cmdline)
        task = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, _ = task.communicate()
        if task.poll() == 0:
            git_ver = out.strip().decode('ascii')
    except:
        pass
    finally:
        os.chdir(cwd)
    return git_ver

#: Version string
version = git_describe()
