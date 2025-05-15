"""Handle :ref:`params_file_format` files in ISF.
"""

from collections.abc import MutableMapping
import json, re, neuron
from data_base.dbopen import dbopen, resolve_modular_db_path

def _read_params_to_dict(filename):
    filename = resolve_modular_db_path(filename)
    with dbopen(filename, "r") as f:
        content = f.read()

    # Replace single quotes with double quotes
    content = content.replace("'", '"')

    # Remove trailing commas using regex
    content = re.sub(r",(\s*[}\]])", r"\1", content)

    # Replace Python-style tuples (x, y) with JSON arrays [x, y]
    content = re.sub(r"\(([^()]+)\)", r"[\1]", content)

    # Replace None with null
    content = content.replace("None", "null")
    
    try:
        params_dict = json.loads(content)
    except json.JSONDecodeError as e:
        line_no = e.lineno
        # Show context around the error with line numbers
        lines = content.split('\n')
        context = '\n'.join(
            f"{i + 1}: {line}" for i, line in enumerate(lines[max(0, line_no-3):min(len(lines), line_no+2)], start=max(0, line_no-3))
        )
        raise ValueError(f"Error decoding .param file with JSON parsing at line {line_no}, col {e.colno}:\n{context}") from e
    return params_dict


def build_parameters(filename):
    """Read in a :ref:`param_file_format` file and return a ParameterSet object.

    Args:
        filename (str): path to the parameter file

    Returns:
        :py:class:`~single_cell_parser.parameters.ParameterSet`: The parameter file as a :py:class:`~single_cell_parser.parameters.ParameterSet` object.
    """
    data = _read_params_to_dict(filename)
    return ParameterSet(data)


def load_NMODL_parameters(parameters):
    """Load NMODL mechanisms from paths in parameter file.

    Parameters are added to the NEURON namespace by executing string Hoc commands.

    See also: https://www.neuron.yale.edu/neuron/static/new_doc/programming/neuronpython.html#important-names-and-sub-packages

    Args:
        parameters (:py:class:`~single_cell_parser.parameters.ParameterSet` | dict):
            The neuron parameters to load.
            Must contain the key `NMODL_mechanisms`.
            May contain the key `mech_globals`.

    Returns:
        None. Adds parameters to the NEURON namespace.
    """
    for mech in list(parameters.NMODL_mechanisms.values()):
        neuron.load_mechanisms(mech)
    try:
        for mech in list(parameters.mech_globals.keys()):
            for param in parameters.mech_globals[mech]:
                paramStr = param + "_" + mech + "="
                paramStr += str(parameters.mech_globals[mech][param])
                print("Setting global parameter", paramStr)
                neuron.h(paramStr)
    except AttributeError:
        pass


class ParameterSet(MutableMapping):
    def __init__(self, data=None):
        if data is None:
            data = {}
        elif isinstance(data, str):
            data = _read_params_to_dict(data)
        elif not isinstance(data, (dict, ParameterSet)):
            raise TypeError(f"Expected dict or filepath, got {type(data)}")
        self._data = {key: self._wrap(value) for key, value in data.items()}

    def _wrap(self, value):
        if isinstance(value, dict):
            return ParameterSet({k: self._wrap(v) for k, v in value.items()})
        elif isinstance(value, list):
            return [self._wrap(v) for v in value]
        return value

    def _unwrap(self, value):
        if isinstance(value, ParameterSet):
            return value.to_dict()
        elif isinstance(value, dict):
            return {k: self._unwrap(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._unwrap(v) for v in value]
        return value

    def to_dict(self):
        return self._unwrap(self._data)

    def save(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

    # --- MutableMapping interface ---
    def __getitem__(self, key):
        return self._resolve_path(key)

    def __setitem__(self, key, value):
        parts = key.split('.')
        current = self._data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = self._wrap(value)

    def __delitem__(self, key):
        parts = key.split('.')
        current = self._data
        for part in parts[:-1]:
            current = current[part]
        del current[parts[-1]]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    # --- Attribute access ---
    def __getattr__(self, name):
        try:
            return self._resolve_path(name)
        except KeyError as e:
            raise AttributeError(f"No such attribute: {name}") from e

    def __setattr__(self, name, value):
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self[name] = value

    def __delattr__(self, name):
        del self[name]

    def _resolve_path(self, dotted):
        parts = dotted.split('.')
        current = self._data
        for part in parts:
            current = current[part]
        return self._wrap(current) if isinstance(current, dict) else current

    def __repr__(self):
        return f"ParameterSet({self._data})"

    def __getstate__(self):
        return self.to_dict()

    def __setstate__(self, state):
        self._data = self._wrap(state)

    def update(self, other=None, **kwargs):
        def deep_merge(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and isinstance(d.get(k), dict):
                    deep_merge(d[k], v)
                else:
                    d[k] = self._wrap(v)
        if other:
            if isinstance(other, dict):
                deep_merge(self._data, other)
            else:
                raise TypeError("update() expects a dict or keyword arguments")
        if kwargs:
            deep_merge(self._data, kwargs)