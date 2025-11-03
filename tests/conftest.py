"""Module conftest.py, reusable code for pytest."""


import pytest
from unittest.mock import patch, mock_open
from pathlib import Path

from src.photo_merger.config_manager import ConfigManager

@pytest.fixture(scope="function", name="mock_yaml_content")
def mock_yaml_config():
    """Fixture that defines a mock config content for file extensions"""
    yaml_content = """
        output_directory_name_suffix: "_suffix"
        allowed_file_extensions:
          - ".jpg"
          - ".jpeg"
          - ".png"
          - ".gif"
          - ".bmp"
          - ".tiff"
          - ".heic"
    """
    return yaml_content


@pytest.fixture(scope="function", name="mock_config")
def test_load_conig_file(mock_yaml_content):
    """Test loading config using mocked open."""
    m_open = mock_open(read_data=mock_yaml_content)

    with patch("src.photo_merger.config_manager.open", m_open):
        config_manager = ConfigManager(Path("mock_config_path.yaml"))
        config = config_manager.load_config_file()

    return config