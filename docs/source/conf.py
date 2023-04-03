import os
import sys

# include ./_ext in path
sys.path.insert(0, os.path.abspath('_ext'))

# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'LMQL'
copyright = '2023, LMQL Language Team'

release = '0.1'
version = '0.1.0'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    "myst_parser",
    "lmql_snippets",
    "nbsphinx"
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_book_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'

html_static_path = ['_static']
html_logo = "logo.png"
html_favicon = "lmql.svg"