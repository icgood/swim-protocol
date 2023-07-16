# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from importlib.metadata import distribution

import cloud_sptheme as csp

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'swim-protocol'
copyright = '2023, Ian Good'
author = 'Ian Good'

# The short X.Y version
project_version = distribution(project).version
version_parts = project_version.split('.')
version = '.'.join(version_parts[0:2])
# The full version, including alpha/beta/rc tags
release = project_version


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.githubpages',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'cloud'
html_theme_path = [csp.get_theme_dir()]
html_static_path = ['_static']

if csp.is_cloud_theme(html_theme):
    html_theme_options = {
        'borderless_decor': True,
        'sidebarwidth': '3in',
        'hyphenation_language': 'en',
    }


# -- Extension configuration -------------------------------------------------

autodoc_member_order = 'bysource'
autodoc_default_options = {'members': True,
                           'show-inheritance': True}
autodoc_typehints = 'description'
autodoc_typehints_format = 'short'
napoleon_numpy_docstring = False

# -- Options for intersphinx extension ---------------------------------------

intersphinx_mapping = {'python': ('https://docs.python.org/3/', None)}
