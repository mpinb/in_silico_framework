"""Handle :ref:`param_file_format` files in ISF.
"""

from collections.abc import MutableMapping, Mapping
from pathlib import Path
import json, re, neuron
from data_base.dbopen import dbopen, resolve_db_path
from data_base import is_data_base


def _make_json_compatible(content):
    # Replace single quotes with double quotes
    content = content.replace("'", '"')

    # Remove trailing commas using regex
    content = re.sub(r",(\s*[}\]])", r"\1", content)

    # Replace Python-style tuples (x, y) with JSON arrays [x, y]
    content = re.sub(r"\(([^()]+)\)", r"[\1]", content)

    # Replace None with null
    content = content.replace("None", "null")

    
    def normalize_path(match):
        # Find patterns that look like Windows paths (starting with drive letter)
        path = match.group(0)
        normalized = path.replace('\\', '/')
        return normalized
    
    # Handle file paths with mixed delimiters - normalize to forward slashes first (works in JSON)
    content = re.sub(r'"[a-zA-Z]:\\[^"]*"', normalize_path, content)

    return content


def _read_params_to_dict(filename):
    filename = resolve_db_path(filename)
    with dbopen(filename, "r") as f:
        content = f.read()

    content = _make_json_compatible(content)

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
    """Read in a :ref:`param_file_format` file and return a NTParameterSet object.

    Args:
        filename (str | Path): path to the parameter file

    Returns:
        :class:`~single_cell_parser.parameters.NTParameterSet`: The parameter file as a :class:`~single_cell_parser.parameters.NTParameterSet` object.
    """
    filename = str(filename)
    data = _read_params_to_dict(filename)
    data = resolve_parameter_paths(data, filename)
    return NTParameterSet(data)


def fast_extract_values_from_param_file_key(param_file, keys, val_is_array=False):
    """Extract parameter values from :ref:`cell_parameters_format` or :ref:`network_parameters_format`.
    
    In contrast to building the parameters using :func:`~build_parameters`, this method uses regex
    to quickly parse out the parameter values. 
    """
    assert not isinstance(keys, str), "You must provide the keys as an array that is not a string"
    
    with open(param_file, 'r') as f:
        content = f.read()
    
    # Create a single regex that captures all keys at once
    if val_is_array:
        key_group = '|'.join(re.escape(key) for key in keys)
        pattern = re.compile(rf"['\"]?({key_group})['\"]?\s*:\s*\[([^\]]*)\],*")
    else:
        key_group = '|'.join(re.escape(key) for key in keys)
        pattern = re.compile(rf"['\"]?({key_group})['\"]?\s*:\s*['\"]([^'\"]*)['\"],*")
    
    # Single pass through the content
    matches = pattern.findall(content)
    
    # Group results by key
    results_dict = {key: [] for key in keys}
    for key_match, value_match in matches:
        if val_is_array:
            items = [item.strip().strip('\'"') for item in value_match.split(',')]
            results_dict[key_match].append(items)
        else:
            results_dict[key_match].append(value_match)
    
    # Return in the same order as input keys
    return [results_dict[key] for key in keys]

    
def load_NMODL_parameters(parameters):
    """Load NMODL mechanisms from paths in parameter file.

    Parameters are added to the NEURON namespace by executing string Hoc commands.

    See also: https://www.neuron.yale.edu/neuron/static/new_doc/programming/neuronpython.html#important-names-and-sub-packages

    Args:
        parameters (:class:`~single_cell_parser.parameters.NTParameterSet` | dict):
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


def resolve_parameter_paths(parameters, params_fn):
    """Resolve relative database paths in the parameters.

    Args:
        parameters (:class:`single_cell_parser.parameters.NTParameterSet`):
            The parameters whose internal paths need to be resolved to the new database location.
        params_fn (str): The path to the parameters file.

    Returns:
        :class:`~single_cell_parser.parameters.NTParameterSet`: The parameters with resolved paths.
    """

    def _find_parent_db_basedir(fn):
        """Find the parent database directory from the parameters."""
        fn = Path(fn)
        parent = fn.parent
        while not is_data_base(parent):
            if parent == parent.parent:  
                # Reached the root directory
                return None
            parent = parent.parent
        return parent

    db_basedir = _find_parent_db_basedir(params_fn)
    
    for key, value in parameters.items():
        if isinstance(value, str) and (value.startswith("reldb://") or value.startswith("mdb://")):
            if db_basedir is None:
                raise ValueError(f"Cannot resolve relative path '{value}', could not find the parent database of {parameters}.")
            parameters[key] = resolve_db_path(value, db_basedir)
        elif isinstance(value, dict):
            parameters[key] = resolve_parameter_paths(value, params_fn)
        elif isinstance(value, list):
            parameters[key] = [resolve_parameter_paths(v, params_fn) if isinstance(v, dict) else v for v in value]

    return parameters

class NTParameterSet(MutableMapping):
    """NeuroTools Parameter Set format.

    Parameters as nested dictionaries, with support for attribute access.

    Example::

        >>> from single_cell_parser.parameters import NTParameterSet
        >>> params = NTParameterSet({'param1': 42, 'nested': {'param2': 3.14}})
        >>> print(params.param1)  # Access via attribute
        42
        >>> print(params['nested.param2'])  # Access via dotted path
        3.14

    Attributes:
        _data (dict): The underlying dictionary storing parameters.
    """
    def __init__(self, data=None):
        if data is None:
            data = {}
        elif isinstance(data, str):
            data = _read_params_to_dict(data)
        elif not isinstance(data, (dict, NTParameterSet)):
            raise TypeError(f"Expected dict or filepath, got {type(data)}")
        self._data = {key: self._wrap(value) for key, value in data.items()}

    def _wrap(self, value):
        if isinstance(value, dict):
            return NTParameterSet({k: self._wrap(v) for k, v in value.items()})
        elif isinstance(value, list):
            return [self._wrap(v) for v in value]
        return value

    def _unwrap(self, value):
        if isinstance(value, NTParameterSet):
            return value.as_dict()
        elif isinstance(value, dict):
            return {k: self._unwrap(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._unwrap(v) for v in value]
        return value

    def as_dict(self):
        """Convert the NTParameterSet to a regular dictionary.

        Returns:
            dict: The underlying dictionary representation of the parameters.
        """
        return self._unwrap(self._data)

    def save(self, filename, **kwargs):
        """Save the NTParameterSet to a file in JSON format.

        Args:
            filename (str): The path to the file where the parameters will be saved.
        """
        indent = kwargs.pop("indent", 4)
        with open(file=filename, mode='w') as f:
            json.dump(obj=self.as_dict(), fp=f, cls=CompactListEncoder, indent=indent, **kwargs)

    def keys(self):
        return self._data.keys()

    
    def tree_copy(self):
        """Return a copy of the ParameterSet tree structure.
        
        Nodes are not copied, but re-referenced. This creates a shallow copy
        of the tree structure where the hierarchy is duplicated but the
        leaf values are shared between original and copy.
        
        Returns:
            :class:`NTParameterSet`: A new :class:`NTParameterSet` with the same structure but shared references to leaf values.
        """
        def _copy_tree_structure(node):
            if isinstance(node, NTParameterSet):
                # Create new NTParameterSet with copied structure
                return NTParameterSet({k: _copy_tree_structure(v) 
                                     for k, v in node._data.items()})
            elif isinstance(node, dict):
                # Create new dict with copied structure
                return {k: _copy_tree_structure(v) for k, v in node.items()}
            elif isinstance(node, list):
                # Create new list with copied structure
                return [_copy_tree_structure(item) for item in node]
            else:
                # Leaf node - return reference (no copying)
                return node
        
        return _copy_tree_structure(self)

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
        return f"NTParameterSet({self._data})"

    def __getstate__(self):
        return self.as_dict()

    def __setstate__(self, state):
        self._data = self._wrap(state)

    def update(self, other=None, **kwargs):
        """Update the NTParameterSet with another dictionary or keyword arguments.

        Args:
            other (dict, optional): Another dictionary to merge into this NTParameterSet.
            kwargs: Additional keyword arguments to merge into this NTParameterSet.
        """
        def deep_update(this, other):
            for other_key, other_value in other.items():
                if isinstance(other_value, Mapping):
                    this[other_key] = deep_update(this=this.get(other_key, {}), other=other_value)
                else:
                    this[other_key] = other_value
            return this
        if isinstance(other, NTParameterSet):
            other = other._data
        deep_update(this=self, other=other)
        return self


class CompactListEncoder(json.JSONEncoder):
    def _encode(self, obj, level):
        indent_str = ' ' * self.indent * level
        inner_indent = ' ' * self.indent * (level + 1)

        if isinstance(obj, list):
            return '[' + ', '.join(self._encode(item, level + 1) for item in obj) + ']'
        if isinstance(obj, dict):
            if not obj:
                return '{}'
            keys = sorted(obj.keys()) if self.sort_keys else obj.keys()
            items = [
                f'{inner_indent}{json.dumps(k, ensure_ascii=self.ensure_ascii)}: {self._encode(v, level + 1)}'
                for k in keys
                for v in [obj[k]]
            ]
            return '{\n' + ',\n'.join(items) + '\n' + indent_str + '}'
        return json.dumps(obj, ensure_ascii=self.ensure_ascii, allow_nan=self.allow_nan, default=self.default)

    def encode(self, obj):
        return self._encode(obj, 0)

    def iterencode(self, obj, _one_shot=False):
        return iter([self.encode(obj)])