# -*- coding: utf-8 -*-
# pylint: disable=broad-except

"""\
Caelus Simulation command
-------------------------
"""

import os
import math
import logging

from ..utils import osutils
from ..utils import pyutils
from .core import CaelusSubCmdScript
from ..io.caelusdict import CaelusDict
from ..run.parametric import CMLParametricRun
from ..config import cmlenv

_lgr = logging.getLogger(__name__)

def determine_sim_json(path=None):
    """Utility to determine the base directory of the Simulation"""
    fname = CMLParametricRun.json_file()
    if path is not None:
        jfile = os.path.join(path, fname)
        if not osutils.path_exists(jfile):
            raise FileNotFoundError("Not a valid sim directory: %s"%
                                    path)
        return jfile
    else:
        wdir = os.getcwd()
        parent = os.path.dirname(wdir)
        json_file = None
        while (parent != wdir):
            jfile = os.path.join(wdir, fname)
            if os.path.exists(jfile):
                json_file = jfile
                break
            wdir = parent
            parent = os.path.dirname(wdir)
        if json_file is None:
            raise FileNotFoundError("Cannot determine sim directory")
        return json_file

class CaelusSimCmd(CaelusSubCmdScript):
    """CLI interface to parametric runs

    This class provides CLI access to CMLParametricRun class

    Subcommands defined:
        - setup    - Setup a new case directory structure
        - prep     - Run pre-processing steps
        - solve    - Run the solvers
        - post     - Run post-processing steps
        - status   - Query status of the runs
    """

    script_levels = ["INFO", "DEBUG"]
    lib_levels = ["INFO", "DEBUG"]

    description = "Caelus Simulation Automation Interface"

    def cli_options(self):
        """Setup sub-commands for CaelusSim"""
        super(CaelusSimCmd, self).cli_options()
        subparsers = self.subparsers

        setup = subparsers.add_parser(
            "setup",
            description="setup a parametric run",
            help="Setup parametric run")
        prep = subparsers.add_parser(
            "prep",
            description="run pre-processing steps",
            help="Run pre-processing steps")
        solve = subparsers.add_parser(
            "solve",
            description="run the solvers",
            help="Run all solvers")
        post = subparsers.add_parser(
            "post",
            description="run post-processing steps",
            help="Run post-processing steps")
        status = subparsers.add_parser(
            "status",
            description="show status of cases in this analysis",
            help="Print out status for the analysis")
        runpy = subparsers.add_parser(
            "runpy",
            description="run a Python script",
            help="Run a python script to process the parametric run")
        shell = subparsers.add_parser(
            "shell",
            description="run an interactive python shell",
            help="Run an interactive shell to process parametric run object")


        # Configuration options
        setup.add_argument(
            '-n', '--sim-name', default=None,
            help="name of this simulation group")
        setup.add_argument(
            '-d', '--base-dir', default=None,
            help="base directory where the simulation structure is created")
        setup.add_argument(
            '-s', '--submit', action='store_true',
            help="submit solve jobs on successful setup")
        setup.add_argument(
            '-p', '--prep', action='store_true',
            help="run pre-processing steps after successful setup")
        setup.add_argument(
            '-f', '--sim-config', default="caelus_sim.yaml",
            help="YAML-formatted simulation configuration (caelus_sim.yaml)")
        setup.set_defaults(func=self.setup)

        prep.add_argument(
            '-d', '--case-dir', default=None,
            help="path to the analysis directory")
        prep.add_argument(
            '-f', '--force', action='store_true',
            help="force re-execution of prep steps")
        prep.add_argument(
            'patterns', nargs='*',
            help="cases to act on")
        prep.set_defaults(func=self.prep)

        solve.add_argument(
            '-d', '--case-dir', default=None,
            help="path to the analysis directory")
        solve.add_argument(
            '-f', '--force', action='store_true',
            help="force re-execution of solve steps")
        solve.add_argument(
            'patterns', nargs='*',
            help="cases to act on")
        solve.set_defaults(func=self.solve)

        post.add_argument(
            '-d', '--case-dir', default=None,
            help="path to the analysis directory")
        post.add_argument(
            '-f', '--force', action='store_true',
            help="force re-execution of post steps")
        post.add_argument(
            'patterns', nargs='*',
            help="cases to act on")
        post.set_defaults(func=self.post)

        status.add_argument(
            '-d', '--case-dir', default=None,
            help="path to the analysis directory")
        status.set_defaults(func=self.status)

        runpy.add_argument(
            '-d', '--case-dir', default=None,
            help="path to the analysis directory")
        runpy.add_argument(
            "python_script",
            help="Path to the python script to run")
        runpy.set_defaults(func=self.runpy)

        shell.add_argument(
            '-d', '--case-dir', default=None,
            help="path to the analysis directory")
        shell.set_defaults(func=self.shell)

    def setup(self):
        """Setup the simulation"""
        args = self.args
        simconf = osutils.abspath(args.sim_config)
        if not osutils.path_exists(simconf):
            _lgr.fatal("Cannot find input file: %s", simconf)
            self.parser.exit(1)

        basedir = args.base_dir or os.getcwd()
        simfile = CaelusDict.load_yaml(simconf)
        simdict = simfile.simulation

        # Fix template path (assume relative to execution directory)
        tmpl_dir = simdict.template.path
        if not os.path.isabs(tmpl_dir):
            simdict.template.path = osutils.abspath(tmpl_dir)

        # Determine name
        name = args.sim_name or simdict.get("sim_name", None)
        if name is None:
            _lgr.fatal("Cannot determine unique name for this simulation")
            self.parser.exit(1)

        env = cmlenv.cml_get_version()
        with osutils.set_work_dir(basedir):
            try:
                _lgr.info("Initializing simulation: %s", name)
                cfdsim = CMLParametricRun(
                    name=name, sim_dict=simdict,
                    env=env, basedir=basedir)
                _lgr.info("Setting up simulation cases: %s", name)
                cfdsim.setup()
                _lgr.info("Successfully setup simulation: %s (%d)",
                          name, len(cfdsim.cases))
            except Exception:
                _lgr.exception("Error setting up simulation")
                self.parser.exit(1)

            try:
                if args.prep or args.submit:
                    _lgr.info("Executing prep for simulation: %s", name)
                    cfdsim.prep()

                if args.submit:
                    _lgr.info("Submitting solve for simulation: %s", name)
                    cfdsim.solve()
            finally:
                cfdsim.save_state()

    def reload_case(self):
        """Reload a previously setup case"""
        dpath = self.args.case_dir
        try:
            json_file = determine_sim_json(path=dpath)
        except FileNotFoundError:
            _lgr.exception("Cannot determine simulation directory")
            self.parser.exit(1)

        casedir = osutils.abspath(os.path.dirname(json_file))
        env = cmlenv.cml_get_version()
        cfdsim = CMLParametricRun.load(env=env, casedir=casedir)
        return cfdsim

    def prep(self):
        """Execute prep"""
        args = self.args
        force = args.force
        cnames = args.patterns or None
        cfdsim = self.reload_case()
        try:
            cfdsim.prep(cnames, force)
        finally:
            cfdsim.save_state()

    def solve(self):
        """Execute prep"""
        args = self.args
        force = args.force
        cnames = args.patterns or None
        cfdsim = self.reload_case()
        try:
            cfdsim.solve(cnames, force)
        finally:
            cfdsim.save_state()

    def post(self):
        """Execute prep"""
        args = self.args
        force = args.force
        cnames = args.patterns or None
        cfdsim = self.reload_case()
        try:
            cfdsim.post(cnames, force)
        finally:
            cfdsim.save_state()

    def shell(self):
        """Execute an interactive shell"""
        cfdsim = self.reload_case()
        try:
            import IPython
            IPython.embed(
                header="caelus_sim iteractive shell. "
                "Use 'cfdsim' to interact with %s"%cfdsim.name,
                colors="neutral")
        except ImportError:
            print("Interactive shell requires IPython installed")
            self.parser.exit(1)
        finally:
            cfdsim.save_state()

    def runpy(self):
        "Execute a python script with a collection"
        args = self.args
        pyscript = args.python_script
        try:
            pymod = pyutils.import_script(pyscript)
        except Exception:
            _lgr.exception("Error importing python script: %s", pyscript)
            self.parser.exit(1)

        if not hasattr(pymod, "main"):
            _lgr.fatal("No main function defined in script: %s", pyscript)
            self.parser.exit(1)

        cfdsim = self.reload_case()
        try:
            getattr(pymod, "main")(cfdsim)
        finally:
            cfdsim.save_state()

    def status(self):
        """Print out status of the cases in this analysis"""
        cfdsim = self.reload_case()
        num_width = math.ceil(math.log10(len(cfdsim.case_names)))
        case_width = max(len(c) for c in cfdsim.case_names)
        tbl_width = num_width + case_width + 25
        line = "="*int(tbl_width)
        fmt = "%%%dd. %%-%ds    %%s"%(num_width, case_width)
        fmt1 = "%%-%ds. %%-%ds    STATUS\n"%(num_width, case_width)
        total = len(cfdsim.case_names)
        failed = 0
        success = 0
        print("\nRun status for: %s"%cfdsim.name)
        print("Directory: %s"%cfdsim.casedir)
        print(line + "\n" + fmt1%("#", "NAME") + line)
        for i, (name, status) in enumerate(cfdsim.status()):
            print(fmt%(i+1, name, status))
            if status == "DONE":
                success += 1
            if status == "FAILED":
                failed += 1
        print(line)
        print("TOTAL = %d; SUCCESS = %d; FAILED = %d"%(total, success, failed))
        print(line + "\n")

def main():
    """Run caelus command"""
    cmd = CaelusSimCmd()
    cmd()
