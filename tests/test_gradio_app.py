"""Smoke test: the Gradio app builds and recalculates from the sliders."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("gradio")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gradio_app  # noqa: E402


def test_app_builds():
    gradio_app.build()


def test_update_follows_the_sliders():
    base = gradio_app.update(0.3, 8.0, 0.3, 0.5, 0.0, "Net Zero 2050")
    more_pass_through = gradio_app.update(0.7, 8.0, 0.3, 0.5, 0.0, "Net Zero 2050")
    assert base[2]["Total (% of equity)"].tolist() == ["2.3", "4.0", "13.0"]
    assert float(more_pass_through[2]["Total (% of equity)"].iloc[-1]) < 13.0
    assert Path(base[-1]).read_bytes()[:2] == b"PK"  # the Word file
