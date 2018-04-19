# -*- coding: utf-8 -*-

"""\
Caelus Python Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :mod:`~caelus.config.config` module provides functions and classes for
loading user configuration via YAML files and a central location to configure
the behavior of the Caelus python library. The user configuration is stored in
a dictionary format within the :class:`~caelus.config.config.CaelusCfg` and can
be modified during runtime by user scripts. Access to the configuration object
is by calling the :func:`get_config` method defined within this module which
returns a fully populated instance of the configuration dictionary. This module
also sets up logging (to both console as well as log files) during the
initialization phase.
"""

import sys
import os
import os.path as pth
import platform
import logging
from logging.config import dictConfig
from ..utils.struct import Struct
from ..utils import osutils
from ..version import version

_rcfile_default = "caelus.yaml"
_rcsys_var = "CAELUSRC_SYSTEM"
_rcfile_var = "CAELUSRC"

_config_banner = """\
# -*- mode: yaml -*-
#
# Caelus Python Library (CPL) %(version)s
#
# Auto-generated on: %(timestamp)s
#

"""

def get_caelus_root():
    """Get Caelus root directory

    In Unix-y systems this returns ``${HOME}/Caelus`` and on Windows it returns
    ``C:\\Caelus``.

    Returns:
        path: Path to Caelus root directory
    """
    sysname = platform.system().lower()
    return (pth.abspath(r'C:\Caelus')
            if "windows" in sysname else
            pth.expanduser('~/Caelus/'))

def get_cpl_root():
    """Return the root path for CPL"""
    ostype = osutils.ostype()
    if ostype == "windows":
        appdir = get_appdata_dir()
        if appdir and os.path.exists(appdir):
            return pth.join(appdir, "caelus")
    else:
        return osutils.abspath("~/.caelus/")


def get_appdata_dir():
    """Return the path to the Windows ``APPDATA`` directory"""
    if "APPDATA" in os.environ:
        return pth.join(os.environ["APPDATA"])
    return None

class CaelusCfg(Struct): # pylint: disable=too-many-ancestors
    """Caelus Configuration Object

    A (key, value) dictionary containing all the configuration data parsed from
    the user configuration files. It is recommended that users obtain an
    instance of this class via the :func:`get_config` function instead of
    directly instantiating this class.
    """

    def write_config(self, fh=sys.stdout):
        """Write configuration to file or standard output.

        Args:
            fh (handle): An open file handle
        """
        fh.write(_config_banner%{
            'timestamp': osutils.timestamp(),
            'version': version,
        })
        self.to_yaml(fh)
        fh.write("\n\n")


def search_cfg_files():
    """Search locations and return all possible configuration files.

    The following locations are searched:

      - The path pointed by :envvar:`CAELUSRC_SYSTEM`

      - The user's home directory :file:`~/.caelus/caelus.yaml` on Unix-like
        systems, and :file:`%APPDATA%/caelus/caelus.yaml` on Windows systems.

      - The path pointed by :envvar:`CAELUSRC`, if defined.

      - The file :file:`caelus.yaml` in the current working directory

    Returns:
        List of configuration files available
    """
    rcfiles = []

    sys_rc = os.environ.get(_rcsys_var, None)
    if sys_rc and pth.exists(sys_rc):
        rcfiles.append(sys_rc)

    sysname = platform.system().lower()
    if "windows" in sysname:
        appdir = get_appdata_dir()
        if appdir:
            rcfile = pth.join(appdir, _rcfile_default)
            if pth.exists(rcfile):
                rcfiles.append(rcfile)

    home = get_caelus_root()
    if home:
        rcfile = pth.join(home, _rcfile_default)
        if pth.exists(rcfile):
            rcfiles.append(rcfile)

    home = get_cpl_root()
    if home:
        rcfile = pth.join(home, _rcfile_default)
        if pth.exists(rcfile):
            rcfiles.append(rcfile)

    env_rc = os.environ.get(_rcfile_var, None)
    if env_rc and pth.exists(env_rc):
        rcfiles.append(env_rc)

    cwd_rc = pth.join(os.getcwd(), _rcfile_default)
    if pth.exists(cwd_rc):
        rcfiles.append(cwd_rc)

    return rcfiles

def configure_logging(log_cfg=None):
    """Configure python logging.

    If ``log_cfg`` is None, then the basic configuration of python logging
    module is used.

    See `Python Logging Documentation <https://docs.python.org/3.6/library/logging.config.html#logging-config-dictschema>`_ for more information.

    Args:
       log_cfg: Instance of :class:`~caelus.config.config.CaelusCfg`
    """
    def get_default_log_file():
        """Set up default logging file if none provided"""
        logs_dir = pth.join(get_cpl_root(), "cpl_logs")
        logs_dir = osutils.ensure_directory(logs_dir)
        return pth.join(logs_dir, "cpl.log")

    if log_cfg is None:
        logging.basicConfig()
    else:
        log_to_file = log_cfg.log_to_file
        log_filename = log_cfg.log_file or get_default_log_file()
        lggr_cfg = log_cfg.pylogger_options

        lggr_cfg.handlers.log_file.filename = log_filename
        if log_to_file:
            lggr_cfg.loggers.caelus.handlers.append("log_file")
        dictConfig(lggr_cfg)
        logger = logging.getLogger(__name__)
        if log_to_file:
            logger.debug("Logging enabled to file: %s", log_filename)

def get_default_config():
    """Return a fresh instance of the default configuration

    This function does not read the ``caelus.yaml`` files on the system, and
    returns the configurations shipped with CPL.

    Returns:
        CaelusCfg: The default configuration
    """
    cdir = pth.dirname(__file__)
    default_yaml = pth.join(cdir, "default_config.yaml")
    cfg = CaelusCfg.load_yaml(default_yaml)
    return cfg

def _cfg_manager():
    """Configuration manager

    Creates an interface to initalize configuration and return the
    configuration instance that can be updated by the user.
    """
    config_files = [None]
    cfg = [None]

    def _init_config(base_cfg=None, init_logging=True):
        """Initialize configuration

        Loads the :func:`get_default_config` and then reads all the
        configuration files available on the system (see
        :func:`search_cfg_files`) and returns a fully populated configuration
        object.

        Args:
            base_cfg (CaelusCfg): A base configuration object that is updated
            init_logging (bool): If True, initializes logging

        Returns:
            CaelusCfg: Configuration object
        """
        cfg = base_cfg or get_default_config()

        rcfiles = search_cfg_files()
        for rcname in rcfiles:
            ctmp = CaelusCfg.load_yaml(rcname)
            cfg.merge(ctmp)

        if init_logging:
            log_cfg = cfg.caelus.logging
            configure_logging(log_cfg)
            logger = logging.getLogger(__name__)
            msg = ("Loaded configuration from files = %s"%rcfiles
               if rcfiles else
                   "No configuration found; using defaults.")
            logger.debug(msg)

        config_files[0] = rcfiles
        return cfg

    def _get_config(base_cfg=None, init_logging=False):
        """Get the configuration object

        On the first call, initializes the configuration object by parsing all
        available configuration files. Successive invocations return the same
        object that can be mutated by the user. The config dictionary can be
        reset by invoking :func:`~caelus.config.config.reload_config`.

        Args:
            base_cfg (CaelusCfg): A base configuration object that is updated
            init_logging (bool): If True, initializes logging

        Returns:
            CaelusCfg: The configuration dictionary
        """
        if cfg[0] is None:
            cfg[0] = _init_config(base_cfg, init_logging)
        return cfg[0]

    def _reset_default_config():
        """Reset to default configuration

        Resets to library default configuration. Unlike
        :func:`~caelus.config.config.reload_config`, this function does not
        load the configuration files.

        Returns:
            CaelusCfg: The configuration dictionary
        """
        cfg[0] = get_default_config()
        return cfg[0]

    def _reload_config(base_cfg=None):
        """Reset the configuration object

        Forces reloading of all the available configuration files and resets
        the modifications made by user scripts.

        See also: :func:`~caelus.config.config.reset_default_config`

        Args:
            base_cfg: A CMLEnv object to use instead of default

        Returns:
            CaelusCfg: The configuration dictionary
        """
        cfg[0] = _init_config(base_cfg)
        return cfg[0]

    def _rcfiles_loaded():
        """Return a list of the configuration files that were loaded"""
        return config_files[0]

    return (_get_config, _reload_config,
            _reset_default_config, _rcfiles_loaded)

(get_config, reload_config,
 reset_default_config,
 rcfiles_loaded) = _cfg_manager()
