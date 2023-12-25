# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import os
import shutil

import pytest

from caelus.run import core as rcore


def test_is_caelus_casedir(template_casedir):
    root = str(template_casedir)
    assert rcore.is_caelus_casedir(root) is True


def test_clean_polymesh(test_casedir):
    root = str(test_casedir)
    meshdir = os.path.join(root, "constant", "polyMesh")
    assert os.path.exists(meshdir)

    # create some dummy files
    fnames = "points faces neighbor owner boundary".split()
    for mfile in fnames:
        fpath = test_casedir.join("constant", "polyMesh", mfile)
        fpath.write("dummy")
    assert os.path.exists(os.path.join(meshdir, "points"))
    for i in range(3):
        fpath = test_casedir.join("constant", "polyMesh", "preserve_%d.dat" % i)
        fpath.write("dummy")

    rcore.clean_polymesh(root, preserve_patterns=["preserve_*.dat"])
    # Ensure that blockMeshDict is protected by default
    assert os.path.exists(os.path.join(root, "system", "blockMeshDict"))
    # Ensure that common mesh files are deleted
    for mfile in fnames:
        assert not os.path.exists(os.path.join(meshdir, mfile))
    # Ensure that preserve patterns are respected
    for i in range(3):
        assert os.path.exists(os.path.join(meshdir, "preserve_%d.dat" % i))


def test_clean_polymesh_noexist(tmpdir):
    """clean_polymesh on a non-existent directory is a no-op"""
    root = str(tmpdir)
    assert not os.path.exists(os.path.join(root, "constant", "polyMesh"))
    rcore.clean_polymesh(root)


def test_clean_casedir(test_casedir):
    root = str(test_casedir)
    logf = test_casedir.join("pisoSolver.log")
    logf.write("logfile")
    uxlog = test_casedir.join("logs", "U.dat")
    uxlog.write("dummy", ensure=True)
    fnames = "points faces neighbor owner boundary".split()
    for mfile in fnames:
        fpath = test_casedir.join("constant", "polyMesh", mfile)
        fpath.write("dummy")

    shutil.copytree(os.path.join(root, "0"), os.path.join(root, "0.orig"))
    rcore.clean_casedir(root, preserve_extra=["0.orig"])

    # Check for files that should exist
    flist = ["0", "0.orig", "Allrun.py", "constant/polyMesh/points"]
    for fname in flist:
        assert os.path.exists(os.path.normpath(os.path.join(root, fname)))
    flist1 = ["pisoSolver.log", "logs/U.dat"]
    for fname in flist1:
        assert not os.path.exists(os.path.normpath(os.path.join(root, fname)))

    # Flip the flags for a full cleanup
    rcore.clean_casedir(root, preserve_zero=False, purge_mesh=True)
    flist2 = ["0", "0.orig", "constant/polyMesh/points"]
    for fname in flist2:
        assert not os.path.exists(os.path.normpath(os.path.join(root, fname)))


def test_clean_casedir_nonexist(tmpdir):
    root = str(tmpdir)
    with pytest.raises(IOError):
        rcore.clean_casedir(root)


def test_clone_casedir(tmpdir, test_casedir):
    tmpldir = str(test_casedir)
    # Prepare template directory with files to be discarded
    test_casedir.mkdir("processor100")
    test_casedir.mkdir("postProcessing")
    fname = test_casedir.join("pisoSolver.log")
    fname.write("dummy")
    fname = test_casedir.join("submit.sh")
    fname.write("dummy")

    casedir = tmpdir.join("cloned_case1")
    root = str(casedir)
    rcore.clone_case(root, tmpldir)
    # Files that must exist
    flist = [
        "0",
        "Allrun.py",
        "system/blockMeshDict",
        "system/controlDict",
        "submit.sh",
    ]
    for froot in flist:
        assert os.path.exists(os.path.normpath(os.path.join(root, froot)))
    # Files that should have been ignored
    flist1 = ["pisoSolver.log", "postProcessing", "processor100"]
    for froot in flist1:
        assert not os.path.exists(os.path.normpath(os.path.join(root, froot)))

    casedir = tmpdir.join("cloned_case2")
    root = str(casedir)
    rcore.clone_case(
        root,
        tmpldir,
        copy_polymesh=False,
        copy_zero=False,
        copy_scripts=False,
        extra_patterns=["sub*.sh"],
    )
    flist = ["constant/RASProperties", "system/controlDict"]
    # Files that must exist with new arguments
    for froot in flist:
        assert os.path.exists(os.path.normpath(os.path.join(root, froot)))
    # Files that must have been ignored
    flist = ["0", "Allrun.py", "constant/polyMesh", "submit.sh"] + flist1
    for froot in flist:
        assert not os.path.exists(os.path.normpath(os.path.join(root, froot)))


def test_find_caelus_recipe_dirs(tmpdir, template_casedir):
    tmpldir = str(template_casedir)
    num_dirs = 5
    fname = "caelus_recipe_test.yaml"
    for i in range(num_dirs):
        cdir = tmpdir.join("casedirs_%d" % i)
        rcore.clone_case(str(cdir), tmpldir)

    assert len(list(rcore.find_case_dirs(str(tmpdir)))) == num_dirs
    for i in range(0, num_dirs, 2):
        fpath = tmpdir.join("casedirs_%d" % i, fname)
        fpath.write("dummy")

    rdirs = list(rcore.find_caelus_recipe_dirs(str(tmpdir), fname))
    assert len(rdirs) == 3


def test_find_recipe_dirs(tmpdir, template_casedir):
    tmpldir = str(template_casedir)
    num_dirs = 5
    fname = "caelus_recipe_test.yaml"
    for i in range(num_dirs):
        cdir = tmpdir.join("casedirs_%d" % i)
        rcore.clone_case(str(cdir), tmpldir)

    assert len(list(rcore.find_case_dirs(str(tmpdir)))) == num_dirs
    for i in range(0, num_dirs, 2):
        fpath = tmpdir.join("casedirs_%d" % i, fname)
        fpath.write("dummy")

    rdirs = list(rcore.find_recipe_dirs(str(tmpdir), fname))
    assert len(rdirs) == 3
