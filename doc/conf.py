# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Prism Pipeline Python API'
copyright = '2023, Prism Software GmbH'
author = 'Richard Frangenberg'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc']

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_static_path = ['_static']

import os
import sys

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Scripts")
sys.path.insert(0, scriptPath)

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Plugins", "Apps", "3dsMax", "Scripts")
sys.path.insert(0, scriptPath)

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Plugins", "Apps", "Blender", "Scripts")
sys.path.insert(0, scriptPath)

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Plugins", "Apps", "Houdini", "Scripts")
sys.path.insert(0, scriptPath)

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Plugins", "Apps", "Maya", "Scripts")
sys.path.insert(0, scriptPath)

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Plugins", "Apps", "Nuke", "Scripts")
sys.path.insert(0, scriptPath)

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Plugins", "Apps", "Photoshop", "Scripts")
sys.path.insert(0, scriptPath)

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Plugins", "Apps", "PureRef", "Scripts")
sys.path.insert(0, scriptPath)

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Plugins", "Apps", "Standalone", "Scripts")
sys.path.insert(0, scriptPath)

scriptPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Prism", "Plugins", "Custom", "Deadline", "Scripts")
sys.path.insert(0, scriptPath)

autodoc_default_flags = ['members']

html_theme = 'sphinx_book_theme'
html_logo = '_static/prism-pipeline-logo.png'
html_title = 'Prism Pipeline Python API Reference'

html_theme_options = {
    "home_page_in_toc": True,
    "use_download_button": True,
    "use_repository_button": True,
    "repository_url": "https://github.com/PrismPipeline/Prism",
    "external_links": [
        ("Prism", "https://prism-pipeline.com"),
    ]
}
