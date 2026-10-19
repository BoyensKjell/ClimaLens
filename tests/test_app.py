"""Smoke test: every page of the web app renders without an error."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGES = ["welcome", "results", "industries", "data", "brief", "how"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page, monkeypatch):
    monkeypatch.setenv("CLIMALENS_PAGE", page)
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception


def test_slider_changes_results():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    before = at.metric[2].value
    at.slider(key="pass_through").set_value(0.6).run()
    assert not at.exception
    assert at.metric[2].value != before
