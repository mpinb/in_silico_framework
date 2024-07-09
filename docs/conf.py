# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
import os
# import mock

# MOCK_MODULES = ['neuron', 'cloudpickle', 'tables', 'distributed', 'mechanisms']
# for mod_name in MOCK_MODULES:
#     sys.modules[mod_name] = mock.Mock()

project = 'In-Silico Framework (ISF)'
copyright = '2023, Arco Bast, Amir Najafgholi, Maria Royo Cano, Rieke Fruengel, Matt Keaton, Bjorge Meulemeester, Omar Valerio'
author = 'Arco Bast, Amir Najafgholi, Maria Royo Cano, Rieke Fruengel, Matt Keaton, Bjorge Meulemeester, Omar Valerio'
release = '0.0.1'
version = '0.0.1'
## Make your modules available in sys.path
project_root = os.path.join(os.path.abspath(os.pardir))
sys.path.append(project_root)
## copy over tutorials
import shutil
shutil.rmtree(os.path.join(project_root, 'docs', 'tutorials'), ignore_errors=True)
shutil.copytree(os.path.join(project_root, 'getting_started', 'tutorials'),
                os.path.join(project_root, 'docs', 'tutorials'))
shutil.copy(os.path.join(project_root, 'getting_started', 'Introduction_to_ISF.ipynb'),
                os.path.join(project_root, 'docs', 'Introduction_to_ISF.ipynb'))
# Figures need to be in the _autosummary directory
if os.path.exists(os.path.join(project_root, 'docs', '_autosummary', '_images')):
    shutil.rmtree(os.path.join(project_root, 'docs', '_autosummary', '_images'))
shutil.copytree(os.path.join(project_root, 'docs', '_static', '_images'),
                os.path.join(project_root, 'docs', '_autosummary', '_images'))


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx_paramlinks',
    'sphinx.ext.viewcode',
    'sphinx.ext.coverage',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'nbsphinx',  # for rendering tutorial notebooks
    'sphinxcontrib.bibtex'  # for citations
]

bibtex_bibfiles = ['bibliography.bib']

# Napoleon settings
napoleon_google_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False  # otherwise custom argument types will not work
napoleon_type_aliases = None
napoleon_attr_annotations = True

## Include Python objects as they appear in source files
## Default: alphabetically ('alphabetical')
# autodoc_member_order = 'bysource'
## Default flags used by autodoc directives
autodoc_default_options = {
    'members': True,
    'show-inheritance': False,
}

autoclass_content = 'both'  # document both the class docstring, as well as __init__
## Generate autodoc stubs with summaries from code
autosummary_generate = ['modules.rst']
autosummary_imported_members = False  # do not show all imported modules per module, this is too bloated
paramlinks_hyperlink_param = 'name'

# Don't run notebooks
nbsphinx_execute = 'never'
pygments_style = "python"
nbsphinx_codecell_lexer = "python"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False  # less verbose for nested packages

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "furo"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "light_logo": "_images/isf-logo-black.png",
    "dark_logo": "_images/isf-logo-white.png",
    "sidebar_hide_name": True,
}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = [
    'default.css',  # relative to html_static_path defined above
    'style.css',
    'downarr.svg'
]

html_js_files = [
    'overview.js'
]

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.

## I don't like links to page reST sources
html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Language to be used for generating the HTML full-text search index.
# Sphinx supports the following languages:
#   'da', 'de', 'en', 'es', 'fi', 'fr', 'h', 'it', 'ja'
#   'nl', 'no', 'pt', 'ro', 'r', 'sv', 'tr'
#html_search_language = 'en'

# A dictionary with options for the search language support, empty by default.
# Now only 'ja' uses this config value
#html_search_options = {'type': 'default'}

# The name of a javascript file (relative to the configuration directory) that
# implements a search results scorer. If empty, the default will be used.
#html_search_scorer = 'scorer.js'