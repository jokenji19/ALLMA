"""All automated tests use disposable working data, never the checkout's archives."""
import pytest


def pytest_addoption(parser):
    parser.addoption('--run-model-integration', action='store_true', default=False,
                     help='Run explicit, locally provisioned model integration tests.')


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--run-model-integration'):
        skip = pytest.mark.skip(reason='Requires --run-model-integration and the pinned model snapshot')
        for item in items:
            if 'model_integration' in item.keywords:
                item.add_marker(skip)


@pytest.fixture(autouse=True)
def isolated_runtime_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
