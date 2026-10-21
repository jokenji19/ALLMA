"""All automated tests use disposable working data, never the checkout's archives."""
import pytest


@pytest.fixture(autouse=True)
def isolated_runtime_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
