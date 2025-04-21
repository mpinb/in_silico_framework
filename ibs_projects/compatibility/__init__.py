from .module_compatibility import (
    init_mdb_backwards_compatibility,
    init_simrun_compatibility,
    init_hay_compatibility
)
#init_mdb_backwards_compatibility()
#init_simrun_compatibility()
# init_hay_compatibility() 

from .module_compatibility import register_package_under_additional_name
register_package_under_additional_name(
    parent_package_name = "ibs_projects", 
    replace_part="ibs_projects", 
    replace_with="project_specific_ipynb_code")
