# -*- coding: utf-8 -*-

"""\
CML Execution Utilities
-----------------------
"""

import sys
import os
import subprocess
import shutil
import logging
import glob
import shlex
from ..utils import osutils
from ..config.cmlenv import cml_get_latest_version

_lgr = logging.getLogger(__name__)

def caelus_execute(cmd, env=None, stdout=sys.stdout, stderr=sys.stderr):
    """Execute a CML command with the right environment setup

    A wrapper around subprocess.Popen to set up the correct environment before
    invoing the CML executable.

    The command can either be a string or a list of arguments as appropriate
    for Caelus executables.

    Examples:
      caelus_execute("blockMesh -help")

    Args:
        cmd (str or list): The command to be executed
        env (CMLEnv): An instance representing the CML installation (default: latest)
        stdout: A file handle where standard output is redirected
        stderr: A file handle where standard error is redirected

    Returns:
        subprocess.Popen : The task instance
    """
    renv = env or cml_get_latest_version()
    cmd_popen = cmd if isinstance(cmd, list) else shlex.split(cmd)
    _lgr.debug("Executing shell command: %s", ' '.join(cmd_popen))
    task = subprocess.Popen(
        cmd_popen, stdout=stdout, stderr=stderr, env=renv.environ)
    return task

def run_cml_exe(cml_exe, casedir=None, env=None,
                logfile=None, wait=True,
                cml_exe_args="", mpi_args=""):
    """Run a CML executable in the given case directory.

    Args:
        casedir (path): Path to the case directory
        cml_exe (str): Name of the executable (e.g., blockMesh, decomposePar, pisoSolver)
        env (CMLEnv): Environment for the Caelus version to use
        logfile (str): Filename for logging outputs (default: ``<cml_exe>.log``)
        wait (bool): If true, wait for the job to complete
        cml_exe_args (str): Arguments passed to the executable
        mpi_args (str): Extra MPI flags passed for parallel runs

    Returns:
        If wait is True, then it returns the status code for the completed job.
        else it returns an instance of subprocess.Popen instance that the user
        can act upon.
    """
    cdir = casedir or os.getcwd()
    with osutils.set_work_dir(cdir):
        logf = logfile or "%s.log"%cml_exe
        cml_cmd = cml_exe + " " + cml_exe_args
        # Ensure it is not a string with just spaces/tabs
        mpargs = mpi_args.strip()
        if mpargs:
            cml_cmd = "mpiexec " + mpi_args + cml_cmd
        with open(logf, 'w') as fh:
            task = caelus_execute(
                cml_cmd, env, stdout=fh, stderr=subprocess.STDOUT)
            if wait:
                status = task.wait()
                if status != 0:
                    _lgr.error("Error running executable %s in %s",
                               cml_exe, cdir)
                return status
            else:
                return task

def is_caelus_casedir(root=None):
    """Check if the path provided looks like a case directory.

    A directory is determined to be an OpenFOAM/Caelus case directory if the
    ``system``, ``constant``, and ``system/controlDict`` exist. No check is
    performed to determine whether the case directory will actually run or if a
    mesh is present.

    Args:
        root (path): Top directory to start traversing (default: CWD)
    """
    casedir_entries = ["constant", "system",
                       os.path.join("system", "controlDict")]
    cdir = os.getcwd() if root is None else root
    return all(os.path.exists(os.path.join(cdir, d))
               for d in casedir_entries)

def find_case_dirs(basedir):
    """Recursively search for case directories existing in a path.

    Args:
        basedir (path): Top-level directory to traverse

    Yields:
        Absolute path to the case directory
    """
    absdir = osutils.abspath(basedir)
    # is the root directory itself a case directory?
    if is_caelus_casedir(absdir):
        yield absdir
    else:
        for root, dirs, _ in os.walk(absdir):
            for d in list(dirs):
                cdir = os.path.join(root, d)
                if is_caelus_casedir(cdir):
                    dirs.remove(d)
                    yield cdir

def find_caelus_recipe_dirs(
        basedir,
        action_file="caelus_tasks.yaml"):
    """Return case directories that contain action files.

    A case directory with action file is determined if the directory succeeds
    checks in :func:`is_caelus_dir` and also contains the action file specified
    by the user.

    Args:
        basedir (path): Top-level directory to traverse
        action_file (filename): Default is ``caelus_tasks.yaml``

    Yields:
        Path to the case directory with action files
    """
    for cdir in find_case_dirs(basedir):
        if os.path.exists(os.path.join(cdir, action_file)):
            yield cdir

def clean_polymesh(casedir,
                   region=None,
                   preserve_patterns=None):
    """Clean the polyMesh from the given case directory.

    Args:
        casedir (path): Path to the case directory
        region (str): Mesh region to delete
        preserve_patterns (list): Shell wildcard patterns of files to preserve
    """
    ppatterns = preserve_patterns or ["blockMeshDict"]
    absdir = osutils.abspath(casedir)
    if not is_caelus_casedir(absdir):
        _lgr.error("Invalid case directory provided: %s", casedir)
        raise FileNotFoundError("Invalid case directory: "+casedir)

    _lgr.debug("Cleaning polyMesh in %s", absdir)
    meshdir = (os.path.join(absdir, "constant", "polyMesh")
               if region is None else
               (os.path.join(absdir, "constant", region, "polyMesh")))
    osutils.clean_directory(meshdir, ppatterns)

def clean_casedir(casedir,
                  preserve_extra=None,
                  preserve_zero=True,
                  purge_mesh=False):
    """Clean a Caelus case directory.

    Cleans files generated by a run. By default, this function will always
    preserve ``system``, ``constant``, and ``0`` directories as well as any
    YAML or python files. Additional files and directories can be preserved by
    using the ``preserve_extra`` option that accepts a list of shell wildcard
    patterns of files/directories that must be preserved.

    Args:
        casedir (path): Absolute path to a case directory.
        preserve_extra (list): List of shell wildcard patterns to preserve
        purge_mesh (bool): If true, also removes mesh from constant/polyMesh
        preserve_zero (bool): If False, removes the 0 directory
    """
    base_patterns = ["system", "constant", "*.yaml", "*.yml", "*.py"]
    zero_pat = ["0"] if preserve_zero else []
    extra_pat = preserve_extra if preserve_extra else []
    ppatterns = base_patterns + zero_pat + extra_pat

    absdir = osutils.abspath(casedir)
    _lgr.debug("Cleaning case directory: %s", absdir)
    osutils.clean_directory(absdir, ppatterns)

    if purge_mesh:
        clean_polymesh(absdir)

def clone_case(casedir,
               template_dir,
               copy_polymesh=True,
               copy_zero=True,
               copy_scripts=True,
               extra_patterns=None):
    """Clone a Caelus case directory.

    Args:
        casedir (path): Absolute path to new case directory.
        template_dir (path): Case directory to be cloned
        copy_polymesh (bool): Copy contents of constant/polyMesh to new case
        copy_zero (bool): Copy time=0 directory to new case
        copy_scripts (bool): Copy python and YAML files
        extra_patterns (list): List of shell wildcard patterns for copying

    Returns:
        path: Absolute path to the newly cloned directory

    Raises:
        IOError: If either the ``casedir`` exists or if the
        ``template_dir`` does not exist or is not a valid Caelus case
        directory.
    """
    absdir = osutils.abspath(casedir)
    tmpl_dir = osutils.abspath(template_dir)
    if os.path.exists(absdir):
        raise IOError("Cannot overwrite existing file/directory: %s", absdir)
    if not (os.path.exists(tmpl_dir) and
            is_caelus_casedir(tmpl_dir)):
        raise IOError("Invalid Caelus case directory provided as template: %s",
                      template_dir)

    default_ignore = ["[1-9]*", "0.[0-9]*", "-[0-9]*",
                      "processor*", "lines",
                      "surfaces", "probes*", "forces*", "sets",
                      "VTK", "*.foam", "surfaceSampling", "postProcessing",
                      "*.log", "log.*", "*logs"]

    if not copy_zero:
        default_ignore += ["0"]
    if not copy_scripts:
        default_ignore += ["*.py", "*.yaml"]
    if not copy_polymesh:
        default_ignore += ["polyMesh"]
    if extra_patterns:
        default_ignore += extra_patterns
    ignore_func = shutil.ignore_patterns(*default_ignore)
    shutil.copytree(tmpl_dir, absdir, ignore=ignore_func)
    _lgr.info("Cloned directory: %s; template directory: %s",
              absdir, tmpl_dir)
    return absdir

def get_mpi_size(casedir):
    """Determine the number of MPI ranks to run"""
    #TODO: Implement decomposeParDict options. How do we handle
    #redistributePar?
    with osutils.set_work_dir(casedir):
        return len(glob.glob("processor*"))
