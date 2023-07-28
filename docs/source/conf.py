import os
import sys

# include ./_ext in path
sys.path.insert(0, os.path.abspath('_ext'))

# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'LMQL Documentation'
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

pygments_style = 'one-dark'

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'shibuya'

html_favicon = "_static/images/lmql.svg"
html_title = "LMQL Docs"

# -- Options for EPUB output
epub_show_urls = 'footnote'

html_static_path = ['_static']
html_logo = "logo.png"
html_favicon = "lmql.svg"

html_theme_options = {
    "light_logo": "_static/logo-light.svg",
    "dark_logo": "_static/logo.svg",
    "twitter_url": "https://twitter.com/lmqllang",
    "github_url": "https://github.com/eth-sri/lmql",
    "nav_links": [
        {
            "title": "Examples",
            "url": "https://lmql.ai/"
        },
        {
            "title": "Playground",
            "url": "https://lmql.ai/playground"
        },
        {
            "title": "Community",
            "url": "https://discord.gg/7eJP4fcyNT"
        }
    ],
    "home_page_in_toc": True,
    "show_navbar_depth": 3,
}