"""Tests for the config_manager module."""

from pathlib import Path

import pydantic
import pytest
import yaml

from photo_merger.config_manager import ConfigManager
from photo_merger.config_model import ConfigModel


# Testing the "load_config_file" method from the "ConfigManager" class.


def test_load_config_file_reads_the_default_configuration() -> None:
    config = ConfigManager().load_config_file()

    assert isinstance(config, ConfigModel)
    assert config.output_directory_name_suffix == "_merged"
    assert ".jpg" in config.allowed_file_extensions


def test_load_config_file_reads_a_custom_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    raw_config = {"output_directory_name_suffix": "_out", "allowed_file_extensions": [".png"]}
    serialized = yaml.safe_dump(raw_config)
    config_path.write_text(serialized)

    config = ConfigManager(config_path=config_path).load_config_file()

    assert config.output_directory_name_suffix == "_out"
    assert config.allowed_file_extensions == [".png"]


def test_load_config_file_rejects_unknown_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    raw_config = {
        "output_directory_name_suffix": "_out",
        "allowed_file_extensions": [],
        "unexpected": True,
    }

    serialized = yaml.safe_dump(raw_config)
    config_path.write_text(serialized)

    with pytest.raises(pydantic.ValidationError):
        ConfigManager(config_path=config_path).load_config_file()
