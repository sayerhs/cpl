# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name

import os.path as pth

from caelus.utils import osutils


def test_ensure_directory(tmpdir):
    """Test ensure_directory"""
    casedir = tmpdir.mkdir("test_case")
    cname = str(casedir)
    newdir = osutils.ensure_directory(pth.join(cname, "test_dir"))
    assert pth.exists(newdir)


def test_backup_file(tmpdir):
    src = tmpdir.join("source.txt")
    src.write("dummy")
    dest_test = osutils.backup_file(str(src))
    tstamp = osutils.timestamp("%Y%m%d-%H%M%S-%Z")
    dest_expect = tmpdir.join("source_" + tstamp + ".txt")
    assert dest_test == dest_expect


def test_misc_osutils():
    osutils.username()
    osutils.user_home_dir()


def test_split_path():
    myfilename = pth.normpath("/home/username/caelus/logs/test.py")
    dname_req = pth.normpath("/home/username/caelus/logs")
    dname, base, ext = osutils.split_path(myfilename)
    if not osutils.ostype() == "windows":
        assert dname == dname_req
    assert base == "test"
    assert ext == ".py"
