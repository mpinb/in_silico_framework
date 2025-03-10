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
        dirup = f"..{os.sep}"
        prefix = ''
        
        # Check relative path
        while link.startswith(dirup):
            prefix += dirup
            link = link[3:]  # module/submodule.py
        # remove backticks from text formatting, just in case
        text = text.replace('`', '')  # module/submodule.py
        
        # Construct the new link
        new_link = f'{dirup}..{os.sep}{api_extension}{os.sep}' + link.lstrip('../').replace('__init__', '').replace('.py', f'{os.sep}index.rst')
        return f"[{text}]({new_link})"
    return pattern.sub(replace_link, content)    
    

def process_notebook(file_path, api_extension="autoapi"):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            notebook_content = json.load(f)
        except Exception as e:
            raise Exception(f"Error reading {file_path}: {e}") from e
    
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