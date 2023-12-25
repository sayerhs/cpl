# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

import os
import shutil

import pytest

from caelus.run import core
from caelus.run.tasks import Tasks
from caelus.utils import osutils
from caelus.utils.struct import Struct

task_yaml = """
tasks:
  - task_set:
      name: RAS
      case_dir: ./c1
      tasks:
        - copy_tree:
            src: srcdir
            dest: destdir
  - task_set:
      name: RAS
      case_dir: ./c2
      tasks:
        - copy_tree:
            src: srcdir
            dest: destdir
"""


def noop_func(*args, **kwargs):
    pass


def test_run_command(test_casedir):
    casedir = str(test_casedir)
    opts = Struct()
    opts.cmd_name = "blockMesh"
    opts.log_file = "blockMesh.log"
    opts.parallel = True
    opts.queue_settings = Struct(num_ranks=12)
    with osutils.set_work_dir(casedir):
        tasks = Tasks()
        tasks.case_dir = casedir
        tasks.cmd_run_command(opts)


def test_copy_files(tmpdir, monkeypatch):
    monkeypatch.setattr(shutil, "copy2", noop_func)
    fname = tmpdir.join("dummy.txt")
    fname.write("dummy")
    opts = Struct(src=str(fname), dest="dummy1.txt")
    with osutils.set_work_dir(str(tmpdir)):
        tasks = Tasks()
        tasks.case_dir = str(tmpdir)
        tasks.cmd_copy_files(opts)


def test_copy_tree(monkeypatch):
    monkeypatch.setattr(shutil, "copytree", noop_func)
    opts = Struct(
        src="srcdir",
        dest="destdir",
        ignore_patterns=["*.txt"],
        preserve_symlinks=False,
    )
    tasks = Tasks()
    tasks.cmd_copy_tree(opts)


def test_clean_case(test_casedir):
    casedir = str(test_casedir)
    opts = Struct(remove_zero=True, remove_mesh=True)
    tasks = Tasks()
    tasks.case_dir = casedir
    tasks.cmd_clean_case(opts)
    assert not os.path.exists(os.path.join(casedir, "0"))


def test_tasks(test_casedir, monkeypatch):
    monkeypatch.setattr(shutil, "copytree", noop_func)
    casedir = str(test_casedir)
    test_casedir.mkdir("c1")
    test_casedir.mkdir("c2")
    task_file = test_casedir.join("caelus_tasks.yaml")
    task_file.write(task_yaml)
    tasks = Tasks.load(task_file=str(task_file))
    tasks(case_dir=casedir)


def test_run_python(tmpdir):
    with osutils.set_work_dir(str(tmpdir)):
        open("test.py", 'w').write("import sys")
        tasks = Tasks()
        opts = Struct(script="test.py")
        tasks.cmd_run_python(opts)

        with pytest.raises(FileNotFoundError):
            opts = Struct(script="test_noexist.py")
            tasks.cmd_run_python(opts)
