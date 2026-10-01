"""Keep legacy tests from writing diaries and default databases into the checkout."""
import pytest


@pytest.fixture(autouse=True)
def isolated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
