# Copyright (C) 2026 Max Lange
# SPDX-License-Identifier: AGPL-3.0-or-later

import os

import app_paths


def test_user_opts_dir_honors_override(monkeypatch, tmp_path):
    override = tmp_path / "custom-opts"
    monkeypatch.setenv("ARIES_USER_OPTS_DIR", str(override))
    assert app_paths.user_opts_dir() == str(override)


def test_user_opts_dir_default_under_app_support(monkeypatch):
    monkeypatch.delenv("ARIES_USER_OPTS_DIR", raising=False)
    path = app_paths.user_opts_dir()
    assert path.endswith(os.path.join("Aries", "Opts"))
