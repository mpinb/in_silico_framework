import os, ast, fnmatch
from functools import lru_cache
from config.isf_logging import logger as isf_logger
logger = isf_logger.getChild("DOCS")
logger.setLevel("INFO")
project_root = os.path.join(os.path.abspath(os.pardir))

def get_module_docstring(module_path):
    """Get the docstring of a module without importing it."""
    try:
        # Find the module's file path
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

@lru_cache(maxsize=None)
def find_modules_with_tag(source_dir, tag=":skip-doc:"):
    """Recursively find all modules with a specific tag in their docstring.
    
    Returns:
        List of module path glob patterns with the tag.
    """
    modules_with_tag = []

    for root, dirs, files in os.walk(source_dir):
        for d in dirs.copy():
            if any([
                fnmatch.fnmatch(
                    os.path.join(root, d), skip) 
                for skip in MODULES_TO_SKIP
            ]):
                dirs.remove(d)
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

def skip_member(app, what, name, obj, skip, options):
    """Skip members if they have the :skip-doc: tag in their docstring.
    
    Note that the object attributes tested for in this function are only compatible
    with the sphinx-autoapi extension. If you are using a different extension, you
    may need to modify this function to use e.g. obj.__doc__ instead of obj.docstring.
    """
    global MODULES_TO_SKIP
    
    # Debug print to check what is being processed
    # print(f"Processing {what}: {name}")
    
    # skip special members, except __get__ and __set__
    short_name = name.rsplit('.', 1)[-1]
    if short_name.startswith('__') and short_name.endswith('__') and name not in ['__get__', '__set__']:
        skip = True
    
    # Skip if it has the :skip-doc: tag
    if not obj.is_undoc_member and ':skip-doc:' in obj.docstring:
        # print(f"Docstring for {name}: {obj.__doc__}")
        skip = True
    
    # Skip inherited members
    if obj.inherited:
        skip = True
    
    if name in MODULES_TO_SKIP:
        skip = True
    
    return skip

MODULES_TO_SKIP = [
    '**tests**', 
    '**barrel_cortex**', 
    '**installer**', 
    '**__pycache__**',
    "**getting_started**",
    "**compatibility**",
    "**.pixi**",
    "**dendrite_thickness**",
    "**mechanisms**",
    "**config**",
    "**docs**",
    "**.ipynb_checkpoints**",
    "**download_google_fonts**"
]
MODULES_TO_SKIP = MODULES_TO_SKIP + find_modules_with_tag(project_root)