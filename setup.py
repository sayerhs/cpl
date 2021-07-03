# -*- coding: utf-8 -*-

"""Caelus Python Library

This python package provides a scriptable interface to Caelus Computational
Mechanics Library (CML).
"""

from setuptools import setup

VERSION = "2.0.0"

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: POSIX",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: Implementation :: CPython",
    "Topic :: Scientific/Engineering :: Physics",
    "Topic :: Scientific/Engineering :: Visualization",
    "Topic :: Utilities",
]

setup(
    name="py-caelus",
    version=VERSION,
    url="http://www.caelus-cml.com",
    license="Apache License, Version 2.0",
    description="Caelus Python Library",
    long_description=__doc__,
    author="Applied CCM",
    maintainer="Applied CCM",
    include_package_data=True,
    platforms="any",
    classifiers=classifiers,
    packages=[
        'caelus',
        'caelus.config',
        'caelus.utils',
        'caelus.post',
        'caelus.run',
        'caelus.io',
        'caelus.scripts',
        'caelus.build',
    ],
    entry_points="""
        [console_scripts]
        caelus=caelus.scripts.caelus:main
        caelus_tutorials=caelus.scripts.caelus_tutorials:main
        caelus_sim=caelus.scripts.caelus_sim:main
    """,
)
