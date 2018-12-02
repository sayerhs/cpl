# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import os
import pytest

from caelus.config import cmlenv
from caelus.io.caelusdict import CaelusDict
from caelus.run.case import CMLSimulation

@pytest.fixture(scope='module')
def cmlsim_casedir(tmpdir_factory):
    basedir = tmpdir_factory.mktemp("__cmlsim_demo")
    casedir = basedir.join("caelus_case")
    return casedir

def test_cmlsim_basic(cmlsim_casedir, template_casedir):
    name = "caelus_case"
    casedir = cmlsim_casedir
    basedir = os.path.dirname(casedir)
    env = cmlenv.cml_get_version()
    case = CMLSimulation(name, env, basedir)
    assert(not os.path.exists(str(casedir)))

    # Test cloning
    case.clone(str(template_casedir))
    assert(os.path.exists(
        os.path.join(str(casedir), "0")))

    # Test clean case method
    case.clean(preserve_zero=False)
    assert(not os.path.exists(
        os.path.join(str(casedir), "0")))

    # Update utility
    case.update(input_mods={})
    assert(case.run_flags["updated"])

    # Persistence capability
    case.save_state()
    jfile = casedir.join(".cmlsimulation.json")
    assert(os.path.exists(str(jfile)))

def test_cmlsim_load(cmlsim_casedir,template_casedir):
    casedir = cmlsim_casedir
    env = cmlenv.cml_get_version()

    case = CMLSimulation.load(env, str(casedir))
    assert(case.run_flags["updated"])
    assert(not case.run_flags["prepped"])
    assert(not case.run_config)

    # Setup run_config
    change_inputs = CaelusDict(
        controlDict=CaelusDict(
            endTime=1,
            writeFormat="binary"
        )
    )
    prep = [CaelusDict(
        copy_tree=CaelusDict(
            src=os.path.join(str(template_casedir), "0"),
            dest=os.path.join(str(casedir), "0")
        )
    )]
    run_config = CaelusDict(
        num_ranks=4,
        mpi_extra_args="-machinefile mymachines",
        queue_settings=dict(account="caelus"),
        reconstruct=False,
        change_inputs=change_inputs,
        prep=prep,
        solve="simpleSolver"
    )
    case.run_config = run_config
    case.save_state()

def test_cmlsim_prep(cmlsim_casedir):
    casedir = cmlsim_casedir
    env = cmlenv.cml_get_version()
    case = CMLSimulation.load(env, str(casedir))
    assert(case.run_config)
    assert(not case.run_flags["prepped"])

    case.prep_case()
    decomp_dict = os.path.join(str(casedir), "system", "decomposeParDict")
    assert(os.path.exists(decomp_dict))
    assert(case.run_flags.prepped)
    case.save_state()

def test_cmlsim_solve(cmlsim_casedir):
    casedir = cmlsim_casedir
    env = cmlenv.cml_get_version()
    case = CMLSimulation.load(env, str(casedir))
    assert(not case.solver)
    assert(not case.run_flags.solve_submitted)

    case.solve()
    assert(case.logfile == "simpleSolver.log")
    assert(case.run_flags.solve_submitted)
    assert(not case.run_flags.solve_completed)
    curr_status = case.status()
    assert(curr_status == "Running")

    # Check status updates
    clog = case.case_log()
    clog.solve_completed = True
    curr_status = case.status()
    assert(curr_status == "Solved")
    case.save_state()

def test_cmlsim_post(cmlsim_casedir):
    casedir = cmlsim_casedir
    env = cmlenv.cml_get_version()
    case = CMLSimulation.load(env, str(casedir))
    assert(case.solver)
    assert(case.run_flags.solve_completed)

    clog = case.case_log()
    clog.solve_completed = True
    case.post_case()
    assert(case.run_flags.post_done)
    assert(not case.run_flags.failed)
