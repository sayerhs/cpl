# -*- coding: utf-8 -*-

"""
Caelus CML Builder
"""

import os
import subprocess
import glob
import multiprocessing
import logging

from ..config import config, cmlenv
from ..utils import osutils

_lgr = logging.getLogger(__name__)

def get_scons_exe(projdir):
    """Return the absolute path to SCons executable shipped with CML

    Args:
        projdir (path): Absolute path to the project directory
    """
    extpath = os.path.join(projdir, "external")
    assert osutils.path_exists(extpath), "Cannot find external directory in: %s"%projdir
    with osutils.set_work_dir(extpath):
        sconsdirs = glob.glob("scons*")
        if sconsdirs:
            # Pick the first directory. CML only distributes one SCons, so we
            # don't bother checking
            scdir = sconsdirs[0]
            ostype = osutils.ostype()
            scons_exe = "scons.bat" if ostype == "windows" else "scons.py"
            scons_exe = os.path.join(extpath, scdir, scons_exe)
            assert osutils.path_exists(scons_exe), "Cannot find SCons executable"
            return scons_exe
        else:
            raise RuntimeError("Cannot determine SCons executable")

class CMLBuilder(object):
    """CPL interface to compile Caelus CML sources"""

    def __init__(self,
                 cml_env=None,
                 scons_exe=None,
                 scons_args=None,
                 build_log=None):
        """
        Args:
            cml_env (CMLEnv): Caelus CML environment information
            scons_exe (path): Path to SCons executable
            scons_args (list): List of arguments to pass to SCons
            build_log (file): Filename to redirect all compiler output
        """
        self.cfg = config.get_config()
        self.env = cml_env or cmlenv.cml_get_latest_version()
        #: Path to scons executable
        self.scons_exe = scons_exe
        #: Arguments to be passed to scons invocation
        self.scons_args = scons_args or []
        self._preprocess_flag = False
        self._write_mode = 'w'
        self.rcode = 0
        cml_logs_dir = os.path.join(
            config.get_cpl_root(), "cml_build_logs")
        cml_logs_dir = osutils.ensure_directory(cml_logs_dir)
        build_log_default = os.path.join(cml_logs_dir, "cml_build.log")

        #: Log file where all output and error are captured
        self.build_log = (build_log or
                            build_log_default)

    def preprocess_scons_args(self):
        """Utility function to preprocess a few SCons args"""
        has_site_dir = any("--site-dir" in x for x in self.scons_args)
        has_install = "install" in self.scons_args
        has_clean = any(c in x
                        for c in ["-c", "--clean", "--remove"]
                        for x in self.scons_args)
        has_jflag = any(j in x
                        for j in ["-j", "--jobs"]
                        for x in self.scons_args)
        if not has_site_dir:
            site_dir = os.path.join(self.env.project_dir, "site_scons")
            site_dir_arg = "--site-dir=%s"%site_dir
            self.scons_args.insert(0, site_dir_arg)
        if not has_jflag:
            nprocs = 1
            try:
                nprocs = multiprocessing.cpu_count()
            except NotImplementedError:
                pass
            self.scons_args.append("--jobs=%d"%nprocs)
        if not (has_install and has_clean):
            self.scons_args.append("install")
        self._preprocess_flag = True

    def build_dir(self, srcdir):
        """Compile sources in given directory

        Args:
            srcdir (path): Path containing sources
        """
        if not self._preprocess_flag:
            self.preprocess_scons_args()
        scons_exe = self.scons_exe or get_scons_exe(self.env.project_dir)
        scons_args = self.scons_args
        srcabs = osutils.abspath(srcdir)
        # Check if this is the top-level directory, otherwise add appropriate
        # flags to SCons
        sconstruct = os.path.join(srcabs, "SConstruct")
        if not osutils.path_exists(sconstruct):
            scons_args = scons_args + ["-u"]
        scons_cmd = [scons_exe] + scons_args
        with open(self.build_log, self._write_mode) as fh:
            fh.write("==> Caelus CML compile start: " +
                     osutils.timestamp() + "\n")
            fh.write("==> Directory: %s\n"%srcabs)
            fh.write("==> Command: " + ' '.join(scons_cmd)+"\n")
            fh.flush()
            with osutils.set_work_dir(srcabs) as _:
                _lgr.info("Starting compilation in: %s", srcabs)
                task = subprocess.Popen(
                    scons_cmd, stdout=fh, stderr=subprocess.STDOUT)
                rcode = task.wait()
                fh.flush()
                if rcode == 0:
                    fh.write("Caelus CML compile completed: " +
                             osutils.timestamp() + "\n")
                    _lgr.info("Compilation succeeded in: %s", srcabs)
                else:
                    _lgr.warning("Compilation failed in: %s", srcabs)
                    self.rcode = rcode
        self._write_mode = 'a'

    def build_project_dir(self):
        """Build Caelus CML project"""
        prjdir = self.env.project_dir
        self.build_dir(prjdir)

    def build_user_dir(self):
        """Build Caelus user directory"""
        userdir = self.env.user_dir
        if osutils.path_exists(userdir):
            self.build_dir(userdir)
            return True
        else:
            _lgr.warning("User directory not found; skipping build")
            return False

class FoamBuilder:
    """OpenFOAM source code compilation interface"""

    def __init__(self,
                 cml_env=None,
                 wmake_args=None,
                 build_log=None):
        """
        Args:
            cml_env (FoamEnv): Caelus Foam environment information
            wmake_args (list): List of arguments to pass to WMake
            build_log (file): Filename to redirect all compiler output
        """
        self.cfg = config.get_config()
        self.env = cml_env or cmlenv.get_version()
        if not isinstance(self.env, cmlenv.FOAMEnv):
            raise ValueError(
                "Attempt to use FoamBuild on non OpenFOAM environment")
        #: Arguments to be passed to Allwmake
        self.wmake_args = wmake_args
        cml_logs_dir = os.path.join(
            config.get_cpl_root(), "cml_build_logs")
        cml_logs_dir = osutils.ensure_directory(cml_logs_dir)
        build_log_default = os.path.join(cml_logs_dir, "cml_build.log")

        #: Log file where all output and error are captured
        self.build_log = (build_log or build_log_default)

        self._write_mode = 'w'
        self.rcode = 0

    def build_dir(self, srcdir):
        """Compile sources in a given directory

        Args:
            srcdir (path): Path containing sources
        """
        srcabs = osutils.abspath(srcdir)
        allwmake_file = os.path.join(srcabs, "Allwmake")
        if not osutils.path_exists(allwmake_file):
            _lgr.error("Cannot build OpenFOAM sources in directory: %s",
                       srcdir)
            self.rcode = 1
            return

        cmd = [allwmake_file] + self.wmake_args
        with open(self.build_log, self._write_mode) as fh:
            fh.write("==> Caelus CML compile start: " +
                     osutils.timestamp() + "\n")
            fh.write("==> Directory: %s\n"%srcabs)
            fh.write("==> Command: " + ' '.join(cmd)+"\n")
            fh.flush()
            with osutils.set_work_dir(srcabs) as _:
                _lgr.info("Starting compilation in: %s", srcabs)
                task = subprocess.Popen(
                    cmd, stdout=fh, stderr=subprocess.STDOUT,
                    env=self.env.environ)
                rcode = task.wait()
                fh.flush()
                if rcode == 0:
                    fh.write("OpenFOAM compile completed: " +
                             osutils.timestamp() + "\n")
                    _lgr.info("Compilation succeeded in: %s", srcabs)
                else:
                    _lgr.warning("Compilation failed in: %s", srcabs)
                    self.rcode = rcode
        self._write_mode = 'a'

    def build_project_dir(self):
        """Build OpenFOAM project directory"""
        self.build_dir(self.env.project_dir)

    def build_user_dir(self):
        """Build OpenFOAM user directory"""
        userdir = self.env.user_dir
        if osutils.path_exists(userdir):
            self.build_dir(userdir)
            return True
        else:
            _lgr.warning("User directory not found; skipping user build")
            return False

def make_cml_builder(cenv, args):
    """Helper function to create a CMLBuilder instance"""
    scons_args = args.build_args
    if args.clean:
        scons_args.append("--clean")
    if args.jobs > 0:
        scons_args.append("--jobs=%d"%args.jobs)
    builder = CMLBuilder(cml_env=cenv,
                            scons_args=scons_args,
                            build_log=args.log_file)
    return builder

def make_foam_builder(cenv, args):
    """Helper function to create a FoamBuilder instance"""
    wmake_args = args.build_args
    if args.clean:
        _lgr.warning("OpenFOAM interface does not support clean")
        return None
    if args.jobs > 0:
        wmake_args.append("-j%d"%args.jobs)
    builder = FoamBuilder(
        cml_env=cenv, wmake_args=wmake_args, build_log=args.log_file)
    return builder

def get_builder(cenv, args):
    """Return a concrete builder instance"""
    if isinstance(cenv, cmlenv.CMLEnv):
        return make_cml_builder(cenv, args)
    elif isinstance(cenv, cmlenv.FOAMEnv):
        return make_foam_builder(cenv, args)
    else:
        _lgr.error("Unknown CML type: %s", cenv)
        return None
