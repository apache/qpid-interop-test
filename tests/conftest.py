import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--large-content",
        action="store_true",
        default=False,
        help="Run extended large content tests (10MB)",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--large-content"):
        skip = pytest.mark.skip(reason="needs --large-content option to run")
        for item in items:
            if "large_content" in item.keywords:
                item.add_marker(skip)
