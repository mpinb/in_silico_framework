# Documentation

Documentation is built automatically using Sphinx. The [configuration file](./conf.py) sets up all the requirements for generating documentation on the fly. Most notably, it enables autosummary, which scans the codebase for docstrings and uses this for the HTML.

For handling each member, we use `sphinx-autoapi`, instead of the usual `autodoc`. This has a lot more flexibility, as autoapi objects expose the following attributes for each member:
- name: the name of the object
- id: the object's id i.e. the fully qualified name (FQN)
- short_name: the object's short name (dropping all prefixes before a .)
- display: whether the object should be displayed (this is the attribute that is modified by this function)
- docstring: the docstring of the object
- type: the type of the object ('method', 'function', 'class', 'data', 'module', 'package')
- children: the children of the object
- summary: the summary of the object (usually the first sentence/line of the docstring)
- url_root: the root of the object's rst filepath relative to this directory (default: /autoapi, which points to the autoapi directory within this directory)
- inherited: whether the object is inherited
- type: the type of the object
- imported: whether the object is imported
- include_path: full path to the object's .rst stub.
- is_private_member: whether the object is a private member
- is_special_member: whether the object is a special member
- is_top_level_object: whether the object is a top level object
- is_undoc_member: whether the object is an undocumented member
- options (list): the options of the object (e.g. 'members', 'undoc-members', 'private-members', 'show-module-summary')
- member_order: ??
- obj: the object itself in dict format, containing the following keys:
    - type: the type of the object ('method', 'function', 'class', 'data', 'module', 'package')
    - name: the name of the object
    - qual_name: non-fully qualified name of the object (e.g. class.method instead of module.class.method)
    - full_name: FQN
    - args: object arguments, fetched from the function definition. Note that these are **not** the arguments parsed from the docstring.
    - doc: the docstring of the object
    - from_line_no: the line number where the object is defined
    - to_line_no: the line number where the object ends (the full object, not only the docstring)
    - return_annotation (bool): whether the object has a return annotation
    - attributes: the object attributes, parsed from the code. Note that these are not taken from the docstring, and thus will likely lack documentation.