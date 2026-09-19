"""Shared fixtures for FLIMPA tests."""

import os
import sys

import pytest

# Headless Qt for CI / sandbox (no display required)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """Single Qt application instance for widget tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture(autouse=True)
def reset_shared_data_singleton():
    """Avoid cross-test pollution from SharedData singleton."""
    from utils.shared_data import SharedData

    SharedData._instance = None
    yield
    SharedData._instance = None
