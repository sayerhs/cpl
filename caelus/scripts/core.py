# -*- coding: utf-8 -*-

"""\
Basic CLI Interface
-------------------

Defines the base classes that are used to build the CLI scripts.
"""

import logging
import argparse
from ..config.config import get_config, configure_logging, rcfiles_loaded
from ..config import cmlenv
from ..version import version

_lgr = logging.getLogger(__name__)

class CaelusScriptBase(object):
    """Base class for all Caelus CLI applications.

    Defines the common functionality for simple scripts and scripts with
    sub-commands that are used to access functionality from the library without
    writing additional python scripts.
    """

    #: Description of the CLI app used in help messages
    description = "Caelus CLI Application"
    #: Epilog for help messages
    epilog = "Caelus Python Library (CPL) %s"%version

    script_levels = ["INFO", "DEBUG"]
    lib_levels = ["WARNING", "INFO", "DEBUG"]

    def __init__(self, name=None, args=None):
        """
        Args:
            name (str): Custom name used in messages
            args (str): Pass arguments instead of using sys.argv
        """
        #: Custom name when invoked from a python interface instead of command
        #: line
        self.name = name
        #: Instance of the ArgumentParser used to parse command line arguments
        self.parser = argparse.ArgumentParser(
            description=self.description,
            epilog=self.epilog,
            prog=name)
        self.cli_options()
        if args:
            #: Arugments provided by user at the command line
            self.args = self.parser.parse_args(args.split())
        else:
            self.args = self.parser.parse_args()

    def cli_options(self):
        """Setup the command line options and arguments"""
        parser = self.parser
        parser.add_argument(
            '--version', action='version',
            version="Caelus Python Library (CPL) %s"%version)
        parser.add_argument(
            '--cml-version', default=None,
            help="CML version used for this invocation")
        verbosity = parser.add_mutually_exclusive_group(required=False)
        verbosity.add_argument(
            '--quiet', action='store_true',
            help="disable informational messages to screen")
        verbosity.add_argument(
            '-v', '--verbose', action='count', default=0,
            help="increase verbosity of logging. Default: No")
        dolog = parser.add_mutually_exclusive_group(required=False)
        dolog.add_argument('--no-log', action='store_true',
                           help="disable logging of script to file.")
        dolog.add_argument('--cli-logs', default=None,
                           help="name of the log file.")

    def __call__(self):
        """Execute the CLI application"""
        args = self.args
        verbosity = args.verbose
        log_to_file = (not args.no_log)
        log_file = args.cli_logs
        self.setup_logging(log_to_file, log_file, verbosity, args.quiet)
        _lgr.info("Caelus Python Library (CPL) %s", version)

        if args.cml_version is not None:
            try:
                cmlenv.cml_get_version(args.cml_version)
            except (RuntimeError, KeyError):
                _lgr.error("Invalid CML version specified: %s",
                           args.cml_version)
                self.parser.exit(1)
            self.cfg.caelus.caelus_cml.default = args.cml_version

    def setup_logging(self, log_to_file=True,
                      log_file=None,
                      verbose_level=0, quiet=False):
        """Setup logging for the script.

        Args:
            log_to_file (bool): If True, script will log to file
            log_file (path): Filename to log
            verbose_level (int): Level of verbosity
        """
        script_levels = self.script_levels
        lib_levels = self.lib_levels
        cfg = get_config(init_logging=False)
        log_cfg = cfg.caelus.logging
        lggr_cfg = log_cfg.pylogger_options
        if quiet:
            lggr_cfg.handlers.console_caelus.level = "ERROR"
            lggr_cfg.handlers.console_script.level = "ERROR"
        else:
            lggr_cfg.handlers.console_caelus.level = (
                lib_levels[min(verbose_level, len(lib_levels)-1)])
            lggr_cfg.handlers.console_script.level = (
                script_levels[min(verbose_level, len(script_levels)-1)])
        lggr_cfg.loggers["caelus.scripts"].handlers.append("log_file")
        log_cfg.log_to_file = log_to_file
        if log_to_file:
            log_cfg.log_file = (log_file or log_cfg.log_file)
        configure_logging(log_cfg)

        rcfiles = rcfiles_loaded()
        msg = ("Loaded configuration from files = %s"%rcfiles
               if rcfiles else
               "No configuration found; using defaults.")
        _lgr.debug(msg)
        if not log_cfg.log_to_file:
            _lgr.warning("Logging to file disabled.")
        self.cfg = cfg

class CaelusSubCmdScript(CaelusScriptBase):
    """A CLI app with sub-commands."""

    def cli_options(self):
        """Setup sub-parsers."""
        super(CaelusSubCmdScript, self).cli_options()
        self.subparsers = self.parser.add_subparsers(
            help="Choose from one of the following sub-commands; use -h to see sub-command options")

    def __call__(self):
        """Execute sub-command"""
        super(CaelusSubCmdScript, self).__call__()
        self.args.func()
