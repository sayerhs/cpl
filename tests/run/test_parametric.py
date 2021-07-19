# -*- coding: utf-8 -*-

"""
Test parametric run setups
"""

from caelus.io.caelusdict import CaelusDict
from caelus.run.parametric import CMLParametricRun

params_yaml = """
simulation:
  sim_name: airfoil_demo

  template:
    path: "%s"

  simulation_setup:
    case_format: "Re_{Re:.1e}/aoa_{aoa:+06.2f}"

    run_matrix:
      - Re: [1.0e6, 2.0e6]
        aoa:
          start: 0.0
          stop: 2.0
          step: 2.0

    constant_parameters:
      density: 1.225
      Uinf: 15.0
      chord: 1.0
      turbKe: 3.75e-07
      turbulenceModel: kOmegaSST

    apply_transforms:
      transform_type: code
      # Only pass these variables to cmlControls
      extract_vars: [velVector, Re, nuValue, liftVector, dragVector]
      # Python code that is executed before generating case parameters
      code: |
        Re = float(Re)
        aoaRad = np.radians(aoa)
        Ux = Uinf * np.cos(aoaRad)
        Uy = Uinf * np.sin(aoaRad)
        velVector = np.array([Ux, Uy, 0.0])
        nuValue = Uinf / Re
        liftVector = np.array([-np.sin(aoaRad), np.cos(aoaRad), 0.0])
        dragVector = np.array([np.cos(aoaRad), np.sin(aoaRad), 0.0])

  # Configuration for running each case within this analysis group
  run_configuration:
    # Number of MPI ranks for parallel runs
    num_ranks: 1

    # Should the case be reconstructed on successful run
    reconstruct: no
"""

def test_parametric(tmpdir, template_casedir):
    yout = params_yaml % (str(template_casedir))
    cdict = CaelusDict.from_yaml(yout)

    sim = CMLParametricRun(
        "test_airfoil", cdict.simulation,
        basedir=str(tmpdir))

    sim.setup()
    stats = list(sim.status())
    assert len(stats) == 4
    sim.save_state()
    assert (tmpdir / "test_airfoil" / sim.json_file()).exists()

    _ = CMLParametricRun.load(casedir=str(tmpdir / "test_airfoil"))
