"""Module for testing config_manager.py"""


from src.photo_merger.config_manager import ConfigModel


def test_load_config_file(mock_config):
    """Testing the 'load_config_file' method."""
    assert isinstance(mock_config, ConfigModel)