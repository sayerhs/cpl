# -*- coding: utf-8 -*-

"""Update construct.yaml
"""

import os
import yaml
import collections 
from six import iteritems

# Maintain ordering of YAML files by replacing simple dict with OrderDict
_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

def dict_representer(dumper, data):
    return dumper.represent_dict(iteritems(data))

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)

# Create system specific contruct.yaml
installer_dir = os.getcwd()
channel_dir = os.path.join(installer_dir, os.pardir, "channels")
channel_dir = os.path.normpath(channel_dir)

yfile = yaml.load(open("construct-template.yaml").read())
if os.name == "nt":
    yfile["channels"][1] = "file:///%s"%channel_dir
else:
    yfile["channels"][1] = "file://%s"%channel_dir

with open("construct.yaml", 'w') as fh:
    yaml.dump(yfile, fh, default_flow_style=False)
