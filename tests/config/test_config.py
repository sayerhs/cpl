# -*- coding: utf-8 -*-

"""
caelus.config.config Tests
"""

import os
import platform

from caelus.config import config


def test_get_caelus_root(monkeypatch):
    """Caelus Root path"""

    def mock_user_tilde(path):
        return "/test_user/Caelus"

    sysname = platform.system().lower()
    if "windows" in sysname:
        assert config.get_caelus_root() == r"C:\Caelus"
    else:
        monkeypatch.setattr(os.path, "expanduser", mock_user_tilde)
        assert config.get_caelus_root() == "/test_user/Caelus"
