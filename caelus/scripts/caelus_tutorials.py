# -*- coding: utf-8 -*-
# pylint: disable=bare-except

"""\
Caelus Tutorial Runner CLI
--------------------------
"""

import os
import fnmatch
import logging

from ..utils import osutils
from ..config.cmlenv import cml_get_version
from ..run import core
from ..run.tasks import Tasks
from .core import CaelusScriptBase

_lgr = logging.getLogger(__name__)

class TutorialRunner(CaelusScriptBase):
    """CLI for running tutorials"""

    description = "Run Caelus Tutorials"

    lib_levels = ["WARNING", "INFO", "DEBUG"]

    def cli_options(self):
        """Setup options for tutorial run interface"""
        super(TutorialRunner, self).cli_options()
        parser = self.parser
        parser.add_argument(
            '-d', '--base-dir', default=os.getcwd(),
            help="directory where tutorials are run")
        parser.add_argument(
            '-c', '--clone-dir', default=None,
            help="copy tutorials from this directory")
        parser.add_argument(
            '--clean', action='store_true',
            help="clean tutorials from this directory")
        parser.add_argument(
            '-f', '--task-file', default="run_tutorial.yaml",
            help="task file containing tutorial actions (run_tutorial.yaml)")
        test_pat = parser.add_mutually_exclusive_group(required=False)
        test_pat.add_argument(
            '-i', '--include-patterns', action='append',
            help="run tutorial case if it matches the shell wildcard pattern")
        test_pat.add_argument(
            '-e', '--exclude-patterns', action='append',
            help="exclude tutorials that match the shell wildcard pattern")

    def get_matching_tutorials(self, basedir):
        """Yield a list of matching tutorials based on patterns."""
        args = self.args
        task_file = args.task_file
        patterns = args.include_patterns
        for cdir in core.find_recipe_dirs(basedir, task_file):
            if any(fnmatch.fnmatch(cdir, pdir)
                   for pdir in patterns):
                yield cdir

    def exclude_matching_tutorials(self, basedir):
        """Yield a list of tutorials that are not excluded by user."""
        args = self.args
        task_file = args.task_file
        patterns = args.exclude_patterns
        for cdir in core.find_recipe_dirs(basedir, task_file):
            if not any(fnmatch.fnmatch(cdir, pdir)
                       for pdir in patterns):
                yield cdir

    def get_all_tutorials(self, basedir):
        """Return all tutorials by walking the directory"""
        args = self.args
        task_file = args.task_file
        for cdir in core.find_recipe_dirs(basedir, task_file):
            yield cdir

    def run_tutorial(self, casedir, cenv):
        """Run actions listed in tutorial task file"""""
        args = self.args
        with osutils.set_work_dir(casedir):
            tasks = Tasks.load(args.task_file)
            tasks(env=cenv)

    def clean_tutorial(self, casedir, cenv):
        """Run clean actions in tutorial task file"""""
        def _exec_clean_case(tasks):
            for task in tasks.tasks:
                for key in task:
                    if key == "clean_case":
                        tasks.cmd_clean_case(task[key])
                        break
                    elif key == "task_set":
                        tasks_sub = Tasks()
                        tasks_sub.case_dir = osutils.abspath(task[key].case_dir)
                        tasks_sub.task_file = tasks.task_file
                        tasks_sub.tasks = task[key].tasks
                        _exec_clean_case(tasks_sub)

        args = self.args
        with osutils.set_work_dir(casedir):
            tasks = Tasks.load(args.task_file)
            tasks.case_dir = casedir
            _exec_clean_case(tasks)

    def run_all_tutorials(self, func):
        """Run all tutorials given by walking the directory"""
        args = self.args

        test_counter = 0
        failed_tests = 0
        cenv = self.cenv
        _lgr.info("Caelus CML version: %s", cenv.version)
        with osutils.set_work_dir(args.base_dir) as wdir:
            for case in func(wdir):
                _lgr.info("Running tutorial: %s", case)
                try:
                    self.run_tutorial(case, cenv)
                except:
                    _lgr.exception("Failed: %s", case)
                    failed_tests += 1
                test_counter += 1
        _lgr.info("Tutorial run complete; Attempted: %d, Failed: %d",
                  test_counter, failed_tests)

    def clean_all_tutorials(self, func):
        """Clean all tutorials given by walking the directory"""
        args = self.args

        test_counter = 0
        failed_tests = 0
        cenv = self.cenv
        _lgr.info("Caelus CML version: %s", cenv.version)
        with osutils.set_work_dir(args.base_dir) as wdir:
            for case in func(wdir):
                try:
                    self.clean_tutorial(case, cenv)
                except:
                    _lgr.warning("Failed clean in: %s", case)
                    failed_tests += 1
                test_counter += 1
        _lgr.info("Tutorial clean complete; Attempted: %d, Failed: %d",
                  test_counter, failed_tests)

    def check_file_argument(self):
        """Check file argument to ensure that there is no directory provided"""
        args = self.args
        fname = args.task_file
        dname = os.path.dirname(fname)
        if dname:
            _lgr.error("Task file pattern should not have directory component; "
                       "use '-d' option to specify base directory")
            self.parser.exit(1)

    def __call__(self):
        """Run the command"""
        super(TutorialRunner, self).__call__()
        self.check_file_argument()
        args = self.args
        func = self.get_all_tutorials
        if args.exclude_patterns:
            func = self.exclude_matching_tutorials
        if args.include_patterns:
            func = self.get_matching_tutorials

        self.cenv = cml_get_version()

        if not args.clean:
            self.run_all_tutorials(func)
        else:
            self.clean_all_tutorials(func)

def main():
    """CLI entry point"""
    cmd = TutorialRunner()
    cmd()
