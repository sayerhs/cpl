# -*- coding: utf-8 -*-

"""
CML Parametric Run Manager
--------------------------
"""

import os
import logging
import itertools
from collections import Mapping

import numpy as np

from ..utils import osutils
from ..io.caelusdict import CaelusDict
from .case import CMLSimCollection

_lgr = logging.getLogger(__name__)


def normalize_variable_param(varspec):
    """Helper function to normalize the different run matrix options"""
    if isinstance(varspec, Mapping):
        start = float(varspec["start"])
        step = float(varspec.get("step", 1))
        stop = float(varspec["stop"]) + 0.5*step
        return np.arange(start, stop, step)

    if isinstance(varspec, (list, np.ndarray)):
        return varspec
    return [varspec]

def iter_case_params(sim_options, case_name_func):
    """Normalize the keys and yield all possible run setups"""
    casefmt = sim_options.get("case_format", "case_{idx:04d}")
    const_params = sim_options.get("constant_parameters", CaelusDict())
    run_matrix = sim_options["run_matrix"]
    code = None
    extract_vars = None
    if "apply_transforms" in sim_options:
        code = sim_options.apply_transforms.code
        extract_vars = sim_options.apply_transforms.get(
            "extract_vars", None)

    idx = 1
    for i, group in enumerate(run_matrix):
        ropts = {k: normalize_variable_param(v)
                 for k, v in group.items()}
        rkeys = ropts.keys()
        rvalues = ropts.values()
        for j, vals in enumerate(itertools.product(*rvalues)):
            rdict = CaelusDict(zip(rkeys, vals))
            rdict.update(const_params)
            myglobs = dict(**rdict)
            myglobs['np'] = np
            mylocs = {}
            if code is not None:
                exec(code, myglobs, mylocs)
                if extract_vars is not None:
                    for k in extract_vars:
                        rdict[k] = mylocs[k]
                else:
                    rdict.update(mylocs)
            case_params = CaelusDict(rdict)
            rdict['idx'] = idx  # Global index
            rdict['gid'] = i    # Group index
            rdict['cid'] = j    # Case index (within this group)
            case_name = case_name_func(
                case_format=casefmt,
                case_params=rdict)
            yield (case_name, case_params)
            idx += 1

class CMLParametricRun(CMLSimCollection):
    """A class to handle parametric runs"""

    _json_public_ = ("name sim_dict case_names _udf_script".split())

    def __init__(self,
                 name,
                 sim_dict,
                 env=None,
                 basedir=None):
        """
        Args:
            name (str): Unique name for this parametric run
            sim_dict (CaelusDict): Dictionary with simulation settings
            env (CMLEnv): CML execution environment
            basedir (path): Path where the parametric run directories are created
        """
        super(CMLParametricRun, self).__init__(name, env, basedir)
        #: Dictionary containing the run settings
        self.sim_dict = sim_dict
        self.udf = self.udf_instance(self.udf_script, self.udf_params)
        self.udf.sim_init_udf(simcoll=self, is_reload=False)

    @property
    def udf_script(self):
        """Return the UDF script"""
        if not hasattr(self, "_udf_script"):
            self._udf_script = self.sim_dict.pop("udf_script", None)
            if self._udf_script is not None:
                self._udf_script = osutils.abspath(self._udf_script)
        return self._udf_script

    @property
    def udf_params(self):
        """Return the parameters for UDF script"""
        return self.sim_dict.get("udf_params", None)

    def setup(self):
        """Setup the parametric case directories"""
        simcfg = self.sim_dict
        tmpl_info = CaelusDict(simcfg.template)
        tmpl_dir = tmpl_info.pop("path")
        setup_params = simcfg.simulation_setup
        runconf = simcfg.run_configuration
        if not osutils.path_exists(tmpl_dir):
            raise FileNotFoundError(
                "Cannot find case template directory: %s"%tmpl_dir)

        cases = []
        if "run_matrix" in setup_params:
            osutils.ensure_directory(self.casedir)
            cases = [self.setup_case(cname, tmpl_dir, cparams, runconf,
                                     tmpl_info)
                     for cname, cparams in
                     iter_case_params(setup_params, self.udf.sim_case_name)]
        self.cases = [case for case in cases if case is not None]
        self.case_names = [case.name for case in self.cases]
        fname = os.path.join(self.casedir, "caelus_sim.yaml")
        with open(fname, 'w') as fh:
            simfile = CaelusDict(simulation=simcfg)
            simfile.to_yaml(fh)

    def setup_case(self, cname, tmpl_dir, cparams, runconf, clone_opts):
        """Helper function to setup the cases"""
        cdir = os.path.join(self.casedir, cname)
        osutils.ensure_directory(os.path.dirname(cdir))
        skip_setup = self.udf.case_setup_prologue(
            name=cname, case_params=cparams, run_config=runconf)

        if skip_setup:
            return None

        case = self.simulation_class()(
            cname, cml_env=self.env,
            basedir=self.casedir, parent=self)
        case.clone(tmpl_dir, **clone_opts)
        case.run_config = runconf
        case.udf = self.udf
        with osutils.set_work_dir(cdir):
            case.update()
            cmlctrls = case.cmlControls
            cmlctrls.data.update(cparams)
            cmlctrls.write()
            self.udf.case_setup_epilogue(case)
        return case
