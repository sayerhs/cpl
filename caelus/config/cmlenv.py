# -*- coding: utf-8 -*-
# pylint: disable=attribute-defined-outside-init,no-else-return

"""\
Caelus CML Environment Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:mod:`~caelus.config.cmlenv` serves as a replacement for Caelus/OpenFOAM bashrc
files, providing ways to discover installed versions as well as interact with
the installed Caelus CML versions. By default, :mod:`cmlenv` attempts to locate
installed Caelus versions in standard locations:
:file:`~/Caelus/caelus-VERSION` on Unix-like systems, and in :file:`C:\Caelus`
in Windows systems. Users can override the default behavior and point to
non-standard locations by customizing their Caelus Python configuration file.

"""

import os
import glob
import shlex
import subprocess
import itertools
import logging
import json
from distutils.version import LooseVersion
from . import config
from ..utils import osutils

_lgr = logging.getLogger(__name__)

def is_foam_var(key):
    """Test if the variable is an OpenFOAM variable"""
    return key.startswith("WM_") or key.startswith("FOAM_")

def discover_versions(root=None):
    """Discover Caelus versions if no configuration is provided.

    If no root directory is provided, then the function attempts to search in
    path provided by :func:`~caelus.config.config.get_caelus_root`.

    Args:
        root (path): Absolute path to root directory to be searched

    """
    def path_to_cfg(caelus_dirs):
        """Convert Caelus directories to configuration objects"""
        for cpath in caelus_dirs:
            bname = os.path.basename(cpath)
            tmp = bname.split("-")
            if tmp:
                version = tmp[-1]
                yield config.CaelusCfg(version=version,
                                       path=cpath)

    rpath = root or config.get_caelus_root()
    cdirs = glob.glob(os.path.join(rpath, "[Cc]aelus-*"))
    return list(path_to_cfg(cdirs))

def _filter_invalid_versions(cml_cfg):
    """Process user configuration and filter invalid versions

    Args:
        cml_cfg (list): List of CML configuration entries
    """
    root_default = config.get_caelus_root()
    for ver in cml_cfg:
        vid = ver.get("version", None)
        if vid is None:
            continue
        # Ensure that the version is not interpreted as a number by YAML
        ver.version = str(vid)
        pdir = ver.get("path",
                       os.path.join(root_default, "caelus-%s"%vid))
        if osutils.path_exists(pdir):
            yield ver


def _determine_platform_dir(root_path):
    """Determine the build type platform option"""
    basepath = os.path.join(root_path, "platforms")
    if not osutils.path_exists(basepath):
        return None

    ostype = osutils.ostype()
    arch_types = ['64', '32']
    compilers = ['g++', 'icpc', 'clang++']
    prec_types = ['DP', 'SP']
    opt_types = ['Opt', 'Prof', 'Debug']

    for at, pt, ot, ct in itertools.product(
            arch_types, prec_types, opt_types, compilers):
        bdir_name = "%s%s%s%s%s"%(ostype, at, ct, pt, ot)
        bdir_path = os.path.join(basepath, bdir_name)
        if osutils.path_exists(bdir_path):
            return bdir_path

def _determine_mpi_dir(root_path, mpi_type="openmpi"):
    """Determine the installed MPI path"""
    basepath = os.path.join(root_path, "external", osutils.ostype())
    mpidirs = glob.glob(os.path.join(basepath, "%s-*"%mpi_type))
    if not mpidirs:
        _lgr.warning("Cannot find MPI directory in %s", basepath)
    elif len(mpidirs) > 1:
        _lgr.warning("Multiple MPI installations found: %s", mpidirs)
    return mpidirs[0] if mpidirs else ""

class CMLEnv(object):
    """CML Environment Interface.

    This class provides an interface to an installed Caelus CML version.
    """

    _root_dir = ""     # Root directory
    _project_dir = ""  # Project directory
    _version = ""      # Version

    def __init__(self, cfg):
        """
        Args:
            cfg (CaelusCfg): The CML configuration object
        """
        self._cfg = cfg
        self._version = cfg.version
        self._project_dir = cfg.get(
            "path",
            os.path.join(config.get_caelus_root(), "caelus-%s"%self.version))
        self._project_dir = osutils.abspath(self._project_dir)
        self._root_dir = os.path.dirname(self._project_dir)

        # Determine build dir
        build_option = cfg.get("build_option", None)
        build_dir = None
        if build_option:
            build_dir = os.path.join(
                self._project_dir, "platforms", build_option)
        else:
            build_dir = _determine_platform_dir(self._project_dir)
        if not build_dir:
            _lgr.debug("Cannot find platform directory: %s",
                       self._project_dir)
            self._build_dir = ""
            self._build_option = ""
        else:
            self._build_dir = build_dir
            self._build_option = os.path.basename(build_dir)

        self._process_scons_env_file()

    def __repr__(self):
        return "<CMLEnv v%s>"%(self.version)

    def __str__(self):
        return "Caleus CML version %s"%(self.version)

    @property
    def root(self):
        """Return the root path for the Caelus install

        Typically on Linux/OSX this is the :file:`~/Caelus` directory.
        """
        return self._root_dir

    @property
    def project_dir(self):
        """Return the project directory path

        Typically :file:`~/Caelus/caelus-VERSION`
        """
        return self._project_dir

    @property
    def version(self):
        """Return the Caelus version"""
        return self._version

    @property
    def build_dir(self):
        """Return the build platform directory"""
        if not self._build_dir or not osutils.path_exists(self._build_dir):
            raise IOError("Cannot find Caelus platform directory: %s"%
                          self._build_dir)
        return self._build_dir

    @property
    def bin_dir(self):
        """Return the bin directory for executable"""
        ostype = osutils.ostype()
        if ostype == "windows":
            return (
                self.lib_dir + os.pathsep +
                self.mpi_libdir + os.pathsep +
                os.path.join(self.build_dir, "bin"))
        else:
            return os.path.join(self.build_dir, "bin")

    @property
    def lib_dir(self):
        """Return the bin directory for executable"""
        return os.path.join(self.build_dir, "lib")

    @property
    def mpi_dir(self):
        """Return the MPI directory for this installation"""
        if not hasattr(self, "_mpi_dir"):
            mpi_dir = self._cfg.get("mpi_root", None)
            if not mpi_dir:
                mpi_dir = _determine_mpi_dir(self.project_dir)
            self._mpi_dir = mpi_dir
        return self._mpi_dir

    @property
    def mpi_libdir(self):
        """Return the MPI library path for this installation"""
        if not hasattr(self, "_mpi_libdir"):
            self._mpi_libdir = self._cfg.get(
                "mpi_lib_path",
                os.path.join(self.mpi_dir, "lib"))
        return self._mpi_libdir

    @property
    def mpi_bindir(self):
        """Return the MPI executables path for this installation"""
        if not hasattr(self, "_mpi_bindir"):
            self._mpi_bindir = self._cfg.get(
                "mpi_bin_path",
                os.path.join(self.mpi_dir, "bin"))
        return self._mpi_bindir

    @property
    def user_dir(self):
        """Return the user directory"""
        if not hasattr(self, "_user_dir"):
            udir = self._cfg.get("user_dir", None)
            if not udir:
                udir = os.path.join(
                    self.root, "%s-%s"%(osutils.username(), self.version))
            self._user_dir = udir
            self._user_build_dir = os.path.join(
                udir, "platforms", self._build_option)
        return self._user_dir

    @property
    def user_libdir(self):
        """Return path to user lib directory"""
        _ = self.user_dir
        return os.path.join(self._user_build_dir, "lib")

    @property
    def user_bindir(self):
        """Return path to user bin directory"""
        _ = self.user_dir
        if osutils.ostype() == "windows":
            return (self.user_libdir +
                    os.path.join(self._user_build_dir, "bin"))
        else:
            return os.path.join(self._user_build_dir, "bin")

    def _generate_environment(self):
        """Return an environment suitable for executing programs"""
        ostype = osutils.ostype()
        senv = os.environ
        senv['PROJECT_DIR'] = self.root
        senv['PROJECT'] = "caelus-%s"%self.version
        senv['CAELUS_PROJECT_DIR'] = self.project_dir
        senv['BUILD_OPTION'] = self._build_option
        senv['EXTERNAL_DIR'] = os.path.join(
            self.project_dir, "external")
        if ostype == "windows":
            win_ext_dir = os.path.normpath(os.path.join(
                self.project_dir, "external", "windows"))
            mingw_bin_dir = os.path.normpath(os.path.join(
                win_ext_dir, "mingw64", "bin"))
            term_bin_dir = os.path.normpath(os.path.join(
                win_ext_dir, "terminal", "bin"))
            ansicon_bin_dir = os.path.normpath(os.path.join(
                win_ext_dir, "ansicon", "x64"))
            senv['PATH'] = (
                self.bin_dir + os.pathsep +
                self.mpi_bindir + os.pathsep +
                self.user_bindir + os.pathsep +
                mingw_bin_dir + os.pathsep +
                term_bin_dir + os.pathsep +
                ansicon_bin_dir + os.pathsep +
                os.environ.get('PATH'))
        else:
            senv['PATH'] = (
                self.bin_dir + os.pathsep +
                self.mpi_bindir + os.pathsep +
                self.user_bindir + os.pathsep +
                os.environ.get('PATH'))
        senv['MPI_BUFFER_SIZE'] = self._scons_env.get(
            'MPI_BUFFER_SIZE', "20000000")
        senv['OPAL_PREFIX'] = self._scons_env.get(
            'OPAL_PREFIX', self.mpi_dir)

        lib_var = 'LD_LIBRARY_PATH'
        if ostype == "darwin":
            lib_var = 'DYLD_FALLBACK_LIBRARY_PATH'
        senv[lib_var] = (
            self.lib_dir + os.pathsep +
            self.mpi_libdir + os.pathsep +
            self.user_libdir + os.pathsep +
            os.environ.get(lib_var, ''))
        return senv

    @property
    def environ(self):
        """Return an environment for running Caelus CML binaries"""
        if not hasattr(self, "_environ"):
            self._environ = self._generate_environment()
        return self._environ

    def _process_scons_env_file(self):
        """Load the CML json file and determine configuration"""
        self._scons_env = {}
        env_file = os.path.join(self.project_dir, "etc", "cml_env.json")
        if osutils.path_exists(env_file):
            env_all = json.load(open(env_file, 'r'))
            env = env_all.get(self._build_option, None)
            if env is not None:
                self._scons_env = env
                self._mpi_libdir = env['MPI_LIB_PATH']
                self._mpi_dir = os.path.dirname(self._mpi_libdir)
                self._user_dir = env['CAELUS_USER_DIR']
                self._user_build_dir = os.path.dirname(
                    env['CAELUS_USER_APPBIN'])
                _lgr.debug(
                    "CML build environment loaded from SCons: %s (%s)",
                           env_file, self._build_option)

class FOAMEnv:
    """OpenFOAM environment interface"""

    _root_dir = ""
    _project_dir = ""
    _version = ""

    def __init__(self, cfg):
        """
        Args:
            cfg (CaleusCfg): The CML configuration object
        """
        self._cfg = cfg
        self._version = cfg.version
        self._project_dir = osutils.abspath(cfg.path)
        self._root_dir = os.path.dirname(self._project_dir)
        self._env = self._process_foam_env(self._project_dir)
        self._build_option = self._env.get("WM_OPTIONS", "")

    def __repr__(self):
        return "<FoamEnv %s>"%(self.version)

    def __str__(self):
        return "OpenFOAM version %s"%(self.version)

    @property
    def root(self):
        """Return the root path for the OpenFOAM install

        Typically on Linux/OSX this is the :file:`~/OpenFOAM` directory.
        """
        return self._root_dir

    @property
    def project_dir(self):
        """Return the project directory path

        Typically :file:`~/Caelus/caelus-VERSION`
        """
        return self._env.get('WM_PROJECT_DIR', self._project_dir)

    @property
    def version(self):
        """Return the project version

        This is the project version as defined in the Caelus configuration
        file. For the exact version reported in OpenFOAM WMake use
        :meth:`foam_version`
        """
        return self._version

    @property
    def foam_version(self):
        """Return the OpenFOAM version

        Unlike ``version`` this reports the version from ``WM_PROJECT_VERSION``
        """
        return self._env.get('WM_PROJECT_VERSION', self._version)

    @property
    def build_option(self):
        """Return the build option"""
        return self._env.get('WM_OPTIONS', "")

    @property
    def build_dir(self):
        """Return the build platform directory"""
        bdir = os.path.join(self.project_dir, "platforms", self._build_option)
        if not osutils.path_exists(bdir):
            raise IOError("Cannot find OpenFOAM platform directory: %s"%
                          bdir)
        return bdir

    @property
    def bin_dir(self):
        """Return the bin directory for executables"""
        bindir = self._env.get("FOAM_APPBIN", '')
        if not os.path.exists(bindir):
            raise IOError("Cannot find OpenFOAM bin directory: %s"%
                          bindir)
        return bindir

    @property
    def lib_dir(self):
        """Return the lib directory for executables"""
        libdir = self._env.get("FOAM_LIBBIN", '')
        if not os.path.exists(libdir):
            raise IOError("Cannot find OpenFOAM lib directory: %s"%
                          libdir)
        return libdir

    @property
    def user_dir(self):
        """Return the user directory"""
        return self._env.get("WM_PROJECT_USER_DIR", '')

    @property
    def user_libdir(self):
        """Return the user lib directory"""
        return self._env.get("FOAM_USER_LIBBIN", '')

    @property
    def user_bindir(self):
        """Return the user binary directory"""
        return self._env.get("FOAM_USER_APPBIN", '')

    @property
    def mpi_dir(self):
        """Return the path to MPI dir"""
        if not hasattr(self, "_mpi_dir"):
            cfg = self._cfg
            if "mpi_root" in cfg:
                self._mpi_dir = cfg["mpi_root"]
            elif "mpi_lib_path" in cfg:
                self._mpi_dir = os.path.dirname(cfg["mpi_lib_path"])
            elif "mpi_bin_path" in cfg:
                self._mpi_dir = os.path.dirname(cfg["mpi_bin_path"])
            else:
                self._mpi_dir = self._env.get('MPI_ARCH_PATH', '')

            if not os.path.exists(self._mpi_dir):
                raise ValueError(
                    "Cannot determine OpenFOAM MPI installation. "
                    "Please specify 'mpi_root' in Caelus configuration.")
        return self._mpi_dir

    @property
    def mpi_libdir(self):
        """Return the path to MPI libraries"""
        if not hasattr(self, "_mpi_libdir"):
            self._mpi_libdir = self._cfg.get(
                "mpi_lib_path",
                os.path.join(self.mpi_dir, "lib"))
        return self._mpi_libdir

    @property
    def mpi_bindir(self):
        """Return the path to MPI binraries"""
        if not hasattr(self, "_mpi_bindir"):
            self._mpi_bindir = self._cfg.get(
                "mpi_bin_path",
                os.path.join(self.mpi_dir, "bin"))
        return self._mpi_bindir

    @property
    def site_libdir(self):
        """Return the site lib directory"""
        return self._env.get("FOAM_SITE_LIBBIN", '')

    @property
    def environ(self):
        """Return the environment"""
        senv = self._env
        senv['PATH'] = (
            self.bin_dir + os.pathsep +
            self.mpi_bindir + os.pathsep +
            self.user_bindir + os.pathsep +
            self._env.get('PATH', ''))
        lib_var = 'LD_LIBRARY_PATH'
        if osutils.ostype() == "darwin":
            lib_var = 'DYLD_FALLBACK_LIBRARY_PATH'
        senv[lib_var] = (
            self.lib_dir + os.pathsep +
            self.mpi_libdir + os.pathsep +
            self.user_libdir + os.pathsep +
            self._env.get(lib_var, ''))
        return senv

    @property
    def foam_bashrc(self):
        """Return the path to the bashrc file"""
        return self._bashrc_file

    def _process_foam_env(self, project_dir):
        """Process the bashrc file and get all necessary variables"""
        extra_vars = "PATH LD_LIBRARY_PATH MPI_ARCH_PATH".split()
        bashrc_path = os.path.join(project_dir, "etc", "bashrc")
        if not os.path.exists(bashrc_path):
            raise FileNotFoundError(
                "Cannot find OpenFOAM config file: %s"%bashrc_path)
        bash_cmd = ("bash --noprofile --norc -c 'source %s && env'"%
                    bashrc_path)
        cmd_env = {k : os.environ.get(k, "")
                   for k in "HOME USER".split()}
        pp = subprocess.Popen(bash_cmd, env=cmd_env,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              shell=True)
        out, _ = pp.communicate()
        retcode = pp.wait()
        if retcode:
            _lgr.exception("Error initializing OpenFOAM environment: %s"%
                           self.version)

        # No errors... process the bash variables
        outbuf = out.decode('UTF-8')
        bash_vars = dict([l.split("=", 1) for l in outbuf.splitlines()
                          if "=" in l])
        foam_keys = [k for k in bash_vars.keys()
                     if is_foam_var(k)]
        env = {k: bash_vars[k] for k in foam_keys}
        env.update((k, bash_vars[k]) for k in extra_vars
                   if k in bash_vars)
        self._adjust_library_path(env)
        self._bashrc_file = bashrc_path
        return env

    def _adjust_library_path(self, env):
        """Adjust the LD_LIBRARY_PATH variable

        Make sure that the paths from the OpenFOAM bashrc file as well as the
        default environment are properly handled in the environment.
        """
        ld_foam = env.get("LD_LIBRARY_PATH", "")
        ld_osenv = os.environ.get("LD_LIBRARY_PATH", "")
        ld_path = os.pathsep.join(ff for ff in [ld_foam, ld_osenv]
                                  if ff)
        if ld_path:
            env['LD_LIBRARY_PATH'] = (ld_path + os.pathsep +
                                      "${LD_LIBRARY_PATH}")

def get_cmlenv_instance(cml):
    """Return a Caelus or OpenFOAM instance

    Args:
        cml (dict): A configuration dictionary
    """
    version = cml.version
    project_dir = cml.get(
        "path",
        os.path.join(config.get_caelus_root(), "caelus-%s"%version))
    if os.path.exists(os.path.join(project_dir, "SConstruct")):
        return CMLEnv(cml)
    elif os.path.exists(os.path.join(project_dir, "wmake")):
        return FOAMEnv(cml)
    else:
        raise FileNotFoundError(
            "Cannot find a proper Caleus/OpenFOAM version: %s"%version)


def _cml_env_mgr():
    """Caelus CML versions manager"""
    cml_versions = {}
    did_init = [False]

    def _init_cml_versions():
        """Initialize versions based on user configuration"""
        cfg = config.get_config()
        cml_opts = cfg.caelus.caelus_cml.versions
        if cml_opts:
            cml_filtered = list(_filter_invalid_versions(cml_opts))
            if cml_opts and not cml_filtered:
                _lgr.warning(
                    "No valid versions provided; check configuration file.")
            for cml in cml_filtered:
                cenv = get_cmlenv_instance(cml)
                cml_versions[cenv.version] = cenv
        else:
            cml_discovered = discover_versions()
            for cml in cml_discovered:
                cenv = get_cmlenv_instance(cml)
                cml_versions[cenv.version] = cenv
        did_init[0] = True

    def _get_latest_version():
        """Get the CML environment for the latest version available.

        Returns:
            CMLEnv: The environment object
        """
        if not cml_versions and did_init[0]:
            raise RuntimeError("No valid Caelus CML versions found")
        else:
            _init_cml_versions()
        vkeys = [LooseVersion(x) for x in cml_versions]
        vlist = sorted(vkeys, reverse=True)
        return cml_versions[vlist[0].vstring]

    def _get_version(version=None):
        """Get the CML environment for the version requested

        If version is None, then it returns the version set as default in the
        configuration file.

        Args:
            version (str): Version string

        Returns:
            CMLEnv: The environment object
        """
        if not cml_versions and did_init[0]:
            raise RuntimeError("No valid Caelus CML versions found")
        else:
            _init_cml_versions()
        cfg = config.get_config()
        vkey = version or cfg.caelus.caelus_cml.get("default",
                                                    "latest")
        if vkey == "latest":
            return _get_latest_version()
        if not vkey in cml_versions:
            raise KeyError("Invalid CML version requested")
        else:
            return cml_versions[vkey]

    def _cml_reset_versions():
        keys = list(cml_versions.keys())
        for key in keys:
            cml_versions.pop(key)
        did_init[0] = False

    return _get_latest_version, _get_version, _cml_reset_versions

(cml_get_latest_version,
 cml_get_version,
 cml_reset_versions) = _cml_env_mgr()
