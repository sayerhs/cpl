# -*- coding: utf-8 -*-

"""Caelus Python Library

This python package provides a scriptable interface to Caelus Computational
Mechanics Library (CML).
"""

from setuptools import setup, find_packages

VERSION = "3.0.0"

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: POSIX",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: Implementation :: CPython",
    "Topic :: Scientific/Engineering :: Physics",
    "Topic :: Scientific/Engineering :: Visualization",
    "Topic :: Utilities",
]


def parse_reqs_file(fname: str):
    """Parse requirements file and return dependencies"""
    with open(fname, 'r') as fh:
        return [line.strip() for line in fh]


install_requires = parse_reqs_file('requirements.txt')


setup(
    name="caelus",
    version=VERSION,
    url="https://sayerhs.github.io/cpl/",
    license="Apache License, Version 2.0",
    description="Caelus Python Library",
    long_description=__doc__,
    author="Shreyas Ananthan, Chris Sideroff",
    maintainer="Shreyas Ananthan, Chris Sideroff",
    include_package_data=True,
    platforms="any",
    classifiers=classifiers,
    packages=[
        'caelus',
        'caelus.build',
        'caelus.config',
        'caelus.fvmesh',
        'caelus.io',
        'caelus.post',
        'caelus.post.funcobj',
        'caelus.run',
        'caelus.scripts',
        'caelus.utils',
    ],
    entry_points="""
        [console_scripts]
        caelus=caelus.scripts.caelus:main
        caelus_tutorials=caelus.scripts.caelus_tutorials:main
        caelus_sim=caelus.scripts.caelus_sim:main
    """,
    python_requires='>=3.10',
    install_requires=install_requires,
)
