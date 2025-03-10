"""Configure modules, functions, methods, classes and attributes so that they are not documented by Sphinx."""
import ast, os
from unittest.mock import patch

project_root = os.path.join(os.path.abspath(os.pardir))
# Global variable to cache the result
_cached_modules_to_skip = None


def skip_member(app, what, name, obj, skip, options):
    """Skip members if they have the :skip-doc: tag in their docstring."""
    # Debug print to check what is being processed
    # print(f"Processing {what}: {name}")
    
    # skip special members, except __get__ and __set__
    if name.startswith('__') and name.endswith('__') and name not in ['__get__', '__set__']:
        return True
    
    # Skip if it has the :skip-doc: tag
    if obj.__doc__ and ':skip-doc:' in obj.__doc__:
        if ':skip-doc:' in obj.__doc__:
            # print(f"Docstring for {name}: {obj.__doc__}")
            print(f"Skipping {what}: {name} due to :skip-doc: tag")
            return True
    
    # Skip inherited members
    if hasattr(obj, '__objclass__') and obj.__objclass__ is not obj.__class__:
        return True
    
    modules_to_skip = find_modules_with_tag(project_root, tag=":skip-doc:")
    if name in modules_to_skip:
        print(f"Skipping {what}: {name} due to :skip-doc: tag in module {obj.__module__}")
        return True
    
    return skip
    
    
def get_module_docstring(module_path):
    """Get the docstring of a module without importing it."""
    try:
        # Find the module's file path
        print("Module path:", module_path)
        if not os.path.isfile(module_path):
            raise FileNotFoundError(f"Module file {module_path} not found")

        # Read the module's source code
        with open(module_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Parse the source code
        parsed_ast = ast.parse(source_code)

        # Extract the docstring
        docstring = ast.get_docstring(parsed_ast)
        return docstring

    except Exception as e:
        print(f"Error getting docstring for module {module_path}: {e}")
        return None

def find_modules_with_tag(source_dir, tag=":skip-doc:"):
    """Recursively find all modules with a specific tag in their docstring.
    
    Returns:
        List of module path glob patterns with the tag.
    """
    modules_with_tag = []

    for root, dirs, files in os.walk(source_dir):
        for f in files:
            if f.endswith(".py"):
                module_path = os.path.join(root, f)
                docstring = get_module_docstring(module_path)
                if docstring and tag in docstring:
                    if "__init__" in module_path:
                        modules_with_tag.append(module_path.rstrip('__init__.py') + "**")
                    else:
                        modules_with_tag.append(module_path + "**")                

    return modules_with_tag


def get_modules_to_skip():
    global _cached_modules_to_skip
    if _cached_modules_to_skip is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        _cached_modules_to_skip = ['**tests**', '**barrel_cortex**', '**installer**', '**__pycache__**'] + find_modules_with_tag(project_root, tag=":skip-doc:")
    return _cached_modules_to_skip

# Use the cached result
modules_to_skip = get_modules_to_skip()