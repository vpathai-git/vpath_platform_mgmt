"""
Pytest configuration and fixtures.

This file is automatically loaded by pytest and can contain:
- Shared fixtures used across multiple test files
- Configuration options
- Test helpers
"""

import pytest


@pytest.fixture
def sample_data():
    """
    Example fixture that provides sample data for tests.

    Usage in tests:
        def test_something(sample_data):
            assert sample_data["key"] == "value"
    """
    return {"key": "value", "number": 42, "items": ["a", "b", "c"]}


@pytest.fixture
def temp_file(tmp_path):
    """
    Fixture that creates a temporary file for testing.

    Usage in tests:
        def test_file_operations(temp_file):
            temp_file.write_text("test content")
            assert temp_file.read_text() == "test content"
    """
    file_path = tmp_path / "test_file.txt"
    yield file_path
    # Cleanup happens automatically when tmp_path is cleaned up


# Add more fixtures as needed for your project
