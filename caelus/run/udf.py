# -*- coding: utf-8 -*-
# pylint: disable=no-self-use,unused-argument

"""\
User-defined functions for CML Simulation
-----------------------------------------

This module defines an interface that can be used to override/customize
behavior of the CMLSimulation classes.
"""

from ..utils.tojson import JSONSerializer

class SimUDFBase(JSONSerializer):
    """Base class for a user-defined function interface.

    This class defines the API for customizing the different steps of a
    simulation and collection.
    """

    def sim_init_udf(self, simcoll, is_reload=False, **kwargs):
        """Steps to execute before a simulation collection is initialized

        Args:
            simcoll (CMLSimCollection): The case collection instance
            is_reload (bool): Flag indicating whether this is a reload
        """

    def sim_epilogue(self, simcoll, **kwargs):
        """Steps to execute at the end before saving state

        Args:
            simcoll (CMLSimCollection): The case collection instance
        """

    def sim_case_name(self,
                      case_format,
                      case_params,
                      **kwargs):
        """Case name generator

        Override this method to customize the default case naming strategy for
        parametric runs.

        Args:
            case_format (str): The case formatter provided in input file
            case_params (CaelusDict): The case parameters dictionary

        """
        print(case_format)
        return case_format.format(**case_params)

    def case_setup_prologue(self, name, case_params, run_config, **kwargs):
        """Customization before a case is setup

        User can manipulate the case_params or the run_config dictionary to
        customize the case setup process. Using this method to customize
        provides a powerful alternative to "apply_transforms" option in
        :class:`CMLParametricRun`.

        The user can return True from the method to skip the
        normal setup and take over setup entirely, or to skip certain cases in
        from the combinations of case parameters possible.

        The name argument is passed for information purposes only. Changing
        this has no effect on the setup process.

        Args:
            name (str): The case name
            case_params (CaelusDict): Parameters for this case
            run_config (CaelusDict): Run configuration for this case

        Return:
            bool: Skip actual setup if True
        """
        skip_setup = False
        return skip_setup

    def case_setup_epilogue(self, case, **kwargs):
        """Customization after a case is setup

        This method is called with one argument, the case instance. The working
        directory is set to the case that has been already setup. For example,
        user can use this method to copy and setup a different polyMesh
        directories when performing mesh refinement studies.

        Args:
            case (CMLSimulation): The case instance
        """

    def case_prep_prologue(self, case, force=False, **kwargs):
        """Customization before prep step is executed.

        Args:
            case (CMLSimulation): The case instance
            force (bool): Force prep if already done

        Return:
            bool: If True, skip default prep steps
        """
        skip_prep = False
        return skip_prep

    def case_prep_epilogue(self, case, force=False, **kwargs):
        """Execute additional steps after default case prep

        Args:
            case (CMLSimulation): The case instance
            force (bool): Force prep even if already done
        """

    def case_post_prologue(self, case, force=False, **kwargs):
        """Customization before post-processing steps are executed

        Args:
            case (CMLSimulation): The case instance
            force (bool): Force post even if already done

        Return:
            bool: Skip default post steps if True
        """
        skip_post = False
        return skip_post

    def case_post_epilogue(self, case, force=False, **kwargs):
        """Execute additional steps after default case post

        Args:
            case (CMLSimulation): The case instance
            force (bool): Force post even if already done
        """
