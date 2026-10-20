"""Smoke test: every page of the web app renders without an error."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGES = ["welcome", "results", "industries", "hotspots", "data", "brief", "how"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page, monkeypatch):
    monkeypatch.setenv("CLIMALENS_PAGE", page)
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception


def test_slider_changes_results(monkeypatch):
    monkeypatch.setenv("CLIMALENS_PAGE", "results")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    before = [m.value for m in at.markdown]
    at.slider(key="pass_through").set_value(0.6).run()
    assert not at.exception
    assert "1 assumption changed" in " ".join(m.value for m in at.markdown)
    assert [m.value for m in at.markdown] != before


def test_reset_restores_base_case(monkeypatch):
    monkeypatch.setenv("CLIMALENS_PAGE", "results")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.slider(key="pass_through").set_value(0.6).run()
    at.button[0].click().run()
    assert at.session_state["pass_through"] == 0.3
    assert "Base case" in " ".join(m.value for m in at.markdown)
