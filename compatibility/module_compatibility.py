'''
register modules and packages under additional names, so that pickle can still import them after a refactor.

Ideally, import statements should never be pickled.
This has happened in the past, for e.g. making Evaluators (typical workflow is to import the "get_Evaluator" from a hay module and adapt from there),
or to import stuff from "project_specific_ipynb_code".

'''

import logging
import sys
from .module_registration import register_package_under_additional_name

logger = logging.getLogger("IBS").getChild(__name__)

# --------------- compatibility with old versions of ISF (only used by the Oberlaender lab in Bonn)
# For old pickled data. 
# This is to ensure backwards compatibility with the Oberlaender lab in MPINB, Bonn. Last adapted on 25/04/2024
# Previous versions of this codebase used pickle as a data format, pickle now tries to import modules that don't exist anymore upon loading
# For this reason, we save the renamed packages/modules under an additional name (i.e. their old name)

def init_simrun_compatibility():
    """
    Registers simrun as a top-level package
    Useful for old pickled data, that tries to import it as a top-level package. simrun has since been moved to simrun3
    """
    import simrun

    # simrun used to be simrun2 and simrun3 (separate packages). 
    # Pickle still wants a simrun3 to exist.
    sys.modules['simrun3'] = simrun
    sys.modules['simrun2'] = simrun
    import simrun.sim_trial_to_cell_object

    # the typo "simtrail" has been renamed to "simtrial"
    # We still assign the old naming here, in case pickle tries to import it.
    simrun.sim_trail_to_cell_object = simrun.sim_trial_to_cell_object
    simrun.sim_trail_to_cell_object.trail_to_cell_object = simrun.sim_trial_to_cell_object.trial_to_cell_object
    simrun.sim_trail_to_cell_object.simtrail_to_cell_object = simrun.sim_trial_to_cell_object.simtrial_to_cell_object


def init_mdb_backwards_compatibility():
    """
    Registers model_data_base as a top-level package
    Useful for old pickled data, that tries to import it as a top-level package. model_data_base has since been moved to :py:mod:`data_base.model_data_base`
    """
    register_package_under_additional_name(
        parent_package_name = "data_base.model_data_base", 
        replace_part="data_base.model_data_base", 
        replace_with="model_data_base"
    )
    register_package_under_additional_name(
        parent_package_name = "data_base.db_initializers", 
        replace_part="data_base.db_initializers", 
        replace_with="model_data_base.mdb_initializers"
    )
    
    import data_base
    import data_base.data_base
    import model_data_base.model_data_base
    model_data_base.model_data_base.get_mdb_by_unique_id = data_base.data_base.get_db_by_unique_id

def init_hay_compatibility():
    """
    Registers the hay package as a top-level package
    Useful for old pickled data, that tries to import it as a top-level package. hay has since been moved to :py:mod:`biophysics_fitting.hay`
    """
    
    module_map = {
        "biophysics_fitting.hay.default_setup": [
            "biophysics_fitting.hay_complete_default_setup", 
            "biophysics_fitting.hay_complete_default_setup_python"],
        "biophysics_fitting.hay.evaluation": [
            "biophysics_fitting.hay_evaluation",
            "biophysics_fitting.hay_evaluation_python"
        ],
        "biophysics_fitting.hay.specification": "biophysics_fitting.hay_specification",
    }
    
    for new_name, old_name in module_map.items():
        if isinstance(old_name, list):
            for name in old_name:
                register_package_under_additional_name(
                    parent_package_name = new_name, 
                    replace_part=new_name, 
                    replace_with=name
                )
        else:
            register_package_under_additional_name(
                parent_package_name = new_name, 
                replace_part=new_name, 
                replace_with=old_name
            )
        