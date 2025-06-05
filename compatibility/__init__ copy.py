from .module_compatibility import (
    init_mdb_backwards_compatibility,
    init_simrun_compatibility,
    init_hay_compatibility
)
from .repo_compatibility import init_repo_compatibility

def run_all():
    init_hay_compatibility()
    init_mdb_backwards_compatibility()
    init_simrun_compatibility()
    init_repo_compatibility()