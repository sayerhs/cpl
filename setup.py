# -*- coding: utf-8 -*-

"""Caelus Python Library

This python package provides a scriptable interface to Caelus Computational
Mechanics Library (CML).
"""

from setuptools import setup, find_packages

VERSION = "4.0.1"

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


setup(
    name="py-caelus",
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
    install_requires=[
        "six>=1.16.0",
        "numpy>=1.26.0",
        "scipy>=1.11.0",
        "pandas>=2.1.0",
        "matplotlib>=3.8.0",
        "PyYAML>=6.0.0",
        "pytz",
        "Jinja2>=3.0.0",
        "ply>=3.11",
        "vtk>=9.2.0",
        "pyvista>=0.42",
    ],
)
