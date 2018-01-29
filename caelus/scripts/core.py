# -*- coding: utf-8 -*-

"""\
Basic CLI Interface
-------------------

Defines the base classes that are used to build the CLI scripts.
"""

import sys
import logging
import argparse
from ..config.config import get_config, configure_logging

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
    epilog = "Caelus Python Library"
    #: Log file
    log_file = "caelus_cli.log"

    def __init__(self, name=None, args=None):
        """
        Args:
            name (str): Custom name used in messages
            args (str): Pass arguments instead of using sys.argv
        """
        self.name = name
        self.parser = argparse.ArgumentParser(
            description=self.description,
            epilog=self.epilog,
            prog=name)
        self.cli_options()
        if args:
            self.args = self.parser.parse_args(args.split())
        else:
            self.args = self.parser.parse_args()

    def cli_options(self):
        """Setup the command line options and arguments"""
        parser = self.parser
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help="Increase verbosity of logging. Default: No")
        dolog = parser.add_mutually_exclusive_group(required=False)
        dolog.add_argument('--no-log', action='store_true',
                           help="Disable logging of script to file.")
        dolog.add_argument('--cli-logs', default=None,
                           help="Name of the log file (%s)"%self.log_file)

    def __call__(self):
        """Execute the CLI application"""
        args = self.args
        verbosity = args.verbose
        log_to_file = (not args.no_log)
        log_file = args.cli_logs
        self.setup_logging(log_to_file, log_file, verbosity)


    def setup_logging(self, log_to_file=True,
                      log_file=None,
                      verbose_level=0):
        """Setup logging for the script.

        Args:
            log_to_file (bool): If True, script will log to file
            log_file (path): Filename to log
        """
        script_levels = ["INFO", "DEBUG"]
        cfg = get_config()
        log_cfg = cfg.caelus.logging
        lggr_cfg = log_cfg.pylogger_options
        lggr_cfg.handlers.console_caelus.level = (
            script_levels[min(verbose_level, 1)])
        lggr_cfg.handlers.console_script.level = (
            script_levels[min(verbose_level, 1)])
        lggr_cfg.loggers["caelus.scripts"].handlers.append("log_file")
        if log_to_file:
            log_cfg.log_to_file = log_to_file
            log_cfg.log_file = (
                log_file or log_cfg.log_file or self.log_file)
        configure_logging(log_cfg)
        if not log_to_file:
            _lgr.warning("Logging to file disabled.")

class CaelusSubCmdScript(CaelusScriptBase):
    """A CLI app with sub-commands."""

    epilog = "Use -h with task to get additional help"

    def cli_options(self):
        """Setup sub-parsers."""
        super(CaelusSubCmdScript, self).cli_options()
        self.subparsers = self.parser.add_subparsers(
            help="Choose from one of the following sub-commands")

    def __call__(self):
        """Execute sub-command"""
        super(CaelusSubCmdScript, self).__call__()
        self.args.func()
