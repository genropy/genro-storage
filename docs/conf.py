"""Sphinx configuration for genro-storage documentation."""

import os
import sys
from datetime import datetime

# Add source to path for autodoc
sys.path.insert(0, os.path.abspath('..'))

# Project information
project = 'genro-storage'
copyright = f'{datetime.now().year}, Genropy Team'
author = 'Genropy Team'
release = '0.1.0-beta'
version = '0.1.0-beta'

# General configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Source file suffixes
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The master toctree document
master_doc = 'index'

# Language
language = 'en'

# HTML output options
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
}

# Autodoc options
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
}

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'fsspec': ('https://filesystem-spec.readthedocs.io/en/latest/', None),
}

# MyST options
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# Mock imports for modules that may not be available during build
autodoc_mock_imports = [
    'fsspec',
    's3fs',
    'gcsfs',
    'adlfs',
    'aiohttp',
]

# Suppress warnings
suppress_warnings = [
    'app.add_directive',  # Suppress directive warnings
    'ref.python',  # Suppress Python object reference warnings
]

# Autodoc type hints
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'
