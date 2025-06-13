import importlib.util
import logging
import pkgutil
import sys
from importlib.util import find_spec
logger = logging.getLogger("IBS").getChild(__name__)

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
    search_locations = parent_package_spec.submodule_search_locations
    
    if search_locations is not None:
        subpackages = []
        for loader, module_or_pkg_name, is_pkg in pkgutil.iter_modules(
            search_locations, 
            parent_package_name+'.'
            ):
            submodule_spec = find_spec(module_or_pkg_name)
            if submodule_spec is None:
                continue
            register_module_or_pkg_old_name(submodule_spec, replace_part=replace_part, replace_with=replace_with)
            if is_pkg:
                subpackages.append(module_or_pkg_name)
        for pkg in subpackages:
            register_package_under_additional_name(pkg, replace_part, replace_with)

