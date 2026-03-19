# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
from importlib.metadata import version as get_version

sys.path.insert(0, os.path.abspath('../..'))

project = 'Pynamic Gain'
copyright = '2024, Friedrich Schwarz, Stefan Pommer, Andreas Neef'
author = 'Friedrich Schwarz, Stefan Pommer, Andreas Neef'
release = get_version("pynamicgain")  # Fetch the version from the installed package
version = release

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx_autodoc_typehints',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.graphviz',
    'sphinx.ext.inheritance_diagram',
]

templates_path = ['_templates']
exclude_patterns = [
    '_build', 
    'Thumbs.db', 
    '**/.DS_Store', 
    '../.idea', 
    '../.git', 
    '**/__pycache__'
]



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_context = {
    "version": version,
}
html_theme_options = {
    "icon_links": [
        {"name": "GitHub", "url": "https://github.com/goecidbn/pynamicgain", "icon": "fab fa-github"},
    ],
    "primary_sidebar_end": ["navbar-icon-links"],
    "show_nav_level": 3,  # Adjust based on your needs
    "navbar_end": ["version", "navbar-icon-links"],
    "header_links_before_dropdown": 6,
}

html_sidebars = {
    "explanations/*": ["sidebar-nav-bs", "navbar-nav"],  # [] to disable
    "index.html": [],
    "_autosummary/*": ["sidebar-nav-bs"],
}
html_css_files = [
    'custom.css',
]
html_static_path = ['_static']
html_title = 'Pynamic Gain'
html_short_title = 'PyDG'
html_favicon = '_static/favicon.ico'


# -- Extension configuration -------------------------------------------------

# Napoleon settings (Google-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True

# autosummary settings
autodoc_member_order = 'bysource'
autoclass_content = 'both'
autodoc_mock_imports = ["git"]
autosummary_generate = True

# intersphinx settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
}

# graphviz settings
graphviz_output_format='svg'