import re
from pathlib import Path
import threading, os
from neuron import h

def _get_mechanism_names(dirname):
    """
    Get the names of the mechanisms in the given path.
    This is used to check if the mechanisms are loaded into NEURON namespace.
    """
    return [
        MechanismParser(os.path.join(dirname, f)).name 
        for f in os.listdir(dirname) 
        if f.endswith('.mod')
    ]


class MechanismParser:
    """Interface to the NEURON namespace for mechanisms
    
    This class provides functionality to check mechanism types, parse `.mod` files, 
    and check if mechanisms are loaded in the NEURON environment.
    It does not load mechanisms directly; instead, it provides a structured way to interact with them.
    """
    _parse_lock = threading.Lock()

    def __init__(self, mod_file):
        if not (isinstance(mod_file, Path) or isinstance(mod_file, str)):
            raise TypeError("mod_file must be a Path or a string representing the path to a .mod file. {} is of type {}".format(mod_file, type(mod_file)))
        if isinstance(mod_file, Path) and not mod_file.exists():
            raise FileNotFoundError(f"{mod_file} does not exist")
        if isinstance(mod_file, str):
            mod_file = Path(mod_file)
        if not os.path.exists(mod_file) or not str(mod_file).endswith(".mod"):
            raise ValueError(f"{mod_file} is not a valid .mod file")

        self.mod_file = mod_file
        self.name = None
        self.mechanism_type = None  # "point_process", "membrane_mechanism", "artificial_cell"

        self._parse_mod_file()

    def _parse_mod_file(self):
        with MechanismParser._parse_lock:
            content = self.mod_file.read_text()

        # Ordered to prefer POINT_PROCESS over SUFFIX if both are present
        match_pp = re.search(r"\bPOINT_PROCESS\s+(\w+)", content)
        match_suffix = re.search(r"\bSUFFIX\s+(\w+)", content)
        match_artificial = re.search(r"\bARTIFICIAL_CELL\s+(\w+)", content)

        if match_pp:
            self.name = match_pp.group(1)
            self.mechanism_type = "point_process"
        elif match_suffix:
            self.name = match_suffix.group(1)
            self.mechanism_type = "membrane_mechanism"
        elif match_artificial:
            self.name = match_artificial.group(1)
            self.mechanism_type = "artificial_cell"
        else:
            raise ValueError(f"No valid NEURON mechanism declaration found in {self.mod_file}")

    def is_loaded(self) -> bool:
        return self.name in h.__dict__

    def __repr__(self):
        return f"<Mechanism name={self.name!r}, type={self.mechanism_type}, loaded={self.is_loaded()}>"