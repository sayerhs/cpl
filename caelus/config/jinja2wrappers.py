# -*- coding: utf-8 -*-

"""
Utilities for working with Jinja2 templates
"""

import os
from jinja2 import Environment, FileSystemLoader

from . import config
from ..version import version
from ..utils import osutils

def get_template_dirs():
    """Return a list of template dirs in normal configuration locations"""
    tmpl_dirs = []

    cfg = config.get_config()
    tmpl_dirs = cfg.caelus.cpl.get("template_dirs", tmpl_dirs)

    home = config.get_cpl_root()
    if home:
        tmpl_path = os.path.join(home, "cpl_templates")
        if os.path.exists(tmpl_path) and os.path.isdir(tmpl_path):
            tmpl_dirs.append(tmpl_path)

    curr_path = os.path.dirname(__file__)
    tmpl_path = os.path.join(curr_path, os.pardir, "templates")
    base_tmpl = [tmpl_path] if os.path.exists(tmpl_path) else []

    return tmpl_dirs + base_tmpl

class CaelusTemplates(object):
    """Interface to interact with Caelus CPL templates"""

    def __init__(self, template_dirs=None):
        """
        Args:
            template_dirs (list): Absolute path to template directories
        """
        tmpl1 = template_dirs or []
        tmpl2 = get_template_dirs()
        all_templates = tmpl1 + tmpl2
        loader = FileSystemLoader(all_templates)
        self.env = Environment(loader=loader)
        gvars = self.env.globals
        gvars['caelus_timestamp'] = osutils.timestamp
        gvars['caelus_version'] = version

    def get_template(self, name):
        """Return the contents of a template indicated by name"""
        return self.env.get_template(name)

    def render_template(self, name, **ctx):
        """Return a string containing the rendered template

        Args:
            name (path): The template name to render
            ctx (dict): Variables for rendering template
        """
        tmpl = self.get_template(name)
        return tmpl.render(ctx)

    def write_template(self, outfile, name, **ctx):
        """Write the rendered template to a file

        Args:
            outfile (path): Absolute path to the output file
            name (path): The template name to render
            ctx (dict): Variables for rendering template
        """
        with open(outfile, 'w') as fh:
            fh.write(self.render_template(name, **ctx))
