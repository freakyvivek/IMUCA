"""
Automated Streamlit App Tests for app.py.

Verifies:
- Headless execution of app.py without unhandled exceptions.
- Unified 10-section dashboard execution.
- Review 1 mode execution (Demo A / Demo B).
"""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_3d_digital_twin_mode_headless():
    """Verify app.py launches in 3D Digital Twin mode by default without exceptions."""
    at = AppTest.from_file(APP_PATH, default_timeout=35)
    at.run()
    assert not at.exception
    # Verify sliders, buttons, and metrics render
    assert len(at.slider) >= 1
    assert len(at.button) >= 4


def test_app_unified_mode_headless():
    """Verify app.py switches to unified 10-section dashboard without exceptions."""
    at = AppTest.from_file(APP_PATH, default_timeout=35)
    at.run()
    if at.sidebar.radio:
        for r in at.sidebar.radio:
            if "Application Mode" in r.label:
                r.set_value("🔬 Unified Multi-Channel System (10 Sections)")
                break
    at.run()
    assert not at.exception
    # Check that 10 tabs rendered
    assert len(at.tabs) >= 10


def test_app_review1_mode_headless():
    """Verify app.py switches to Review 1 mode and renders without exceptions."""
    at = AppTest.from_file(APP_PATH, default_timeout=35)
    at.run()
    # Switch application mode to Review 1
    if at.sidebar.radio:
        for r in at.sidebar.radio:
            if "Application Mode" in r.label:
                r.set_value("⚡ Single-Point / Sweep DC Voltage Analyzer (Review 1 Baseline)")
                break
    at.run()
    assert not at.exception
    # In Review 1 mode, 9 tabs should be present
    assert len(at.tabs) == 9

