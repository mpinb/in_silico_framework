import json, re, os, shutil

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def convert_links_to_sphinx(content, api_extension="autoapi"):
    """Parse out markdown links of the form `[link text](../module/submodule.py)` and replace them with 
    external links to the Sphinx documentation web page.
    
    Args:
        content (str): The content to convert. Normally a single line of html
        api_extension (str): The extension used for the API documentation.
            Used to determine the location of the stub file (i.e. the .rst file, but without the .rst suffix).
            Options: 'autoapi' or 'autosummary'.
        
    """
    # Regular expression to find Markdown links to Python files
    pattern = re.compile(r'\[([^\]]+)\]\(([^)]+\.py)\)')
    
    # Replace Markdown links with Sphinx directives
    def replace_link(match):
        # example: `[link text](../module/submodule.py)`
        text = match.group(1)  # name of the link: link text
        link = match.group(2)  # path to the Python file: ../module/submodule.py
        
        # Identify the prefix (leading ../)
        prefix = ''
        while link.startswith('../'):
            prefix += '../'
            link = link[3:]  # module/submodule.py
        # remove backticks from text formatting, just in case
        text = text.replace('`', '')  # module/submodule.py
        
        # Construct the new link
        module_doc_name = link.replace('/', '.').replace('.py', '').lstrip('.')  # module.submodule
        module_doc_name = module_doc_name.replace('.__init__', '')  # in case the module is actually module.__init__.py
        if api_extension == 'autoapi':
            module_doc_relative_path = link.replace('.py', '').lstrip('.').replace('/__init__', '')  # relative within the autoapi directory
            module_doc_path = f'{prefix}autoapi/{module_doc_relative_path}'
            new_link = f'{module_doc_path}/index.html#module-{module_doc_name}' # ../autoapi/path/to/file/index.html#module-path/to/file
        elif api_extension == 'autosummary':
            new_link = f'{prefix}_autosummary/{module_doc_name}.html#module-{module_doc_name}'
        else:
            raise NotImplementedError(f"api_extension '{api_extension}' is not supported. Options are: 'autoapi' or 'autosummary'.")
        return f"<a> href=\"{new_link}\" >{text}</a>"
    
    return pattern.sub(replace_link, content)

def process_notebook(file_path, api_extension="autoapi"):
    with open(file_path, 'r', encoding='utf-8') as f:
        notebook_content = json.load(f)
    
    # Process each cell in the notebook
    for cell in notebook_content['cells']:
        if cell['cell_type'] == 'markdown':
            cell['source'] = [convert_links_to_sphinx(line, api_extension=api_extension) for line in cell['source']]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(notebook_content, f, indent=2)

def copy_and_parse_notebooks_to_docs(
    source_dir=os.path.join(project_root, 'getting_started', 'tutorials'),
    dest_dir=os.path.join(project_root, 'docs', 'tutorials'),
    api_extension="autoapi",
    ):
    """Copy notebooks from the source directory to the destination directory and parse the links.
    
    Removes the destination directory if it already exists.
    """
    
    def ignore_checkpoints(dir, files):
        return [f for f in files if f == '.ipynb_checkpoints']
    
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.copytree(source_dir, dest_dir, ignore=ignore_checkpoints)
    
    # Process each notebook in the destination directory
    for root, _, files in os.walk(dest_dir):
        for f in files:
            if f.endswith('.ipynb'):
                process_notebook(os.path.join(root, f), api_extension=api_extension)