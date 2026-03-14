"""Pytest configuration."""

import pytest
from beartype import beartype

pytest_plugins = "sphinx.testing.fixtures"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply the beartype decorator to all collected test functions."""
    for item in items:
        if isinstance(item, pytest.Function):
            item.obj = beartype(obj=item.obj)
