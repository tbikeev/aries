# Copyright (C) 2026 Max Lange
# SPDX-License-Identifier: AGPL-3.0-or-later

from webapp.daemon.style_profile_service import style_profile_css_overrides


def test_color_alias_renders_as_css_var_reference():
    profile = {
        "overrides": {
            "chart.color.signs": "{chart.color.frame}",
            "chart.color.frame": [75, 75, 102],
        }
    }
    rendered = style_profile_css_overrides(profile)
    assert rendered["--morinus-signs"] == "var(--morinus-frame)"
    assert rendered["--morinus-frame"] == "rgb(75 75 102)"


def test_literal_rgba_renders_with_alpha():
    profile = {
        "overrides": {
            "chart.color.background": [16, 16, 16, 0.5],
        }
    }
    rendered = style_profile_css_overrides(profile)
    assert rendered["--morinus-background"] == "rgb(16 16 16 / 50%)"
