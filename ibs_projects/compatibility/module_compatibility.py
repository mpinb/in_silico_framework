'''
register modules and packages under additional names, so that pickle can still import them after a refactor.

Ideally, import statements should never be pickled.
This has happened in the past, for e.g. making Evaluators (typical workflow is to import the "get_Evaluator" from a hay module and adapt from there),
or to import stuff from "project_specific_ipynb_code".

'''

import importlib.util
import logging
import pkgutil
import sys
from importlib.util import find_spec

logger = logging.getLogger("ISF").getChild(__name__)

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


def register_module_or_pkg_old_name(module_spec, replace_part, replace_with):
    additional_module_name = module_spec.name.replace(replace_part, replace_with)
    logger.debug("Registering module \"{}\" under the name \"{}\"".format(module_spec.name, additional_module_name))
    
    # Create a lazy loader for the module
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[additional_module_name] = module
    
    module_spec.loader.exec_module(module)

    # Ensure the parent module is aware of its submodule
    parent_module_name = additional_module_name.rsplit('.', 1)[0]
    if parent_module_name in sys.modules:
        parent_module = sys.modules[parent_module_name]
        submodule_name = additional_module_name.split('.')[-1]
        setattr(parent_module, submodule_name, module)


def register_package_under_additional_name(parent_package_name, replace_part, replace_with):
    parent_package_spec = find_spec(parent_package_name)
    if parent_package_spec is None:
        raise ImportError(f"Cannot find package {parent_package_name}")
    
    register_module_or_pkg_old_name(parent_package_spec, replace_part=replace_part, replace_with=replace_with)
    
    subpackages = []
    for loader, module_or_pkg_name, is_pkg in pkgutil.iter_modules(
        parent_package_spec.submodule_search_locations, 
        parent_package_name+'.'
        ):
        submodule_spec = find_spec(module_or_pkg_name)
        if submodule_spec is None:
            continue
        if module_or_pkg_name == "ibs_projects.compatibility":
            continue
        register_module_or_pkg_old_name(submodule_spec, replace_part=replace_part, replace_with=replace_with)
        if is_pkg:
            subpackages.append(module_or_pkg_name)
    for pkg in subpackages:
        register_package_under_additional_name(pkg, replace_part, replace_with)

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
    
    import data_base
    import data_base.data_base
    import model_data_base.model_data_base
    model_data_base.model_data_base.get_mdb_by_unique_id = data_base.data_base.get_db_by_unique_id

def init_hay_compatibility():
    """
    Registers the hay package as a top-level package
    Useful for old pickled data, that tries to import it as a top-level package. hay has since been moved to :py:mod:`biophysics_fitting.hay`
    """
    hay_modules = {
        "hay.default_setup": "hay_complete_default_setup", 
        "hay.evaluation": "hay_evaluation"
    }

    for replace_part, replace_with in hay_modules.items():
        module_name = "biophysics_fitting."+ replace_part
        module_spec = find_spec(module_name)
        register_module_or_pkg_old_name(
                module_spec = module_spec, 
                replace_part=replace_part, 
                replace_with=replace_with)
