"""Module for loading and validating the photo-merger configuration file."""

import logging
from pathlib import Path

import yaml

from photo_merger.config_model import ConfigModel
from photo_merger.constants import CONFIG_PATH

logger = logging.getLogger(__name__)


class ConfigManager:
    """Load and validate the config file into a ConfigModel.

    Attributes:
        config_path (Path): Path to the YAML configuration file.

    Example:
        >>> config = ConfigManager().load_config_file()
        >>> config.output_directory_name_suffix
        '_merged'
    """

    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        """Store the path to the config file for later reading.

        Args:
            config_path (Path): Path to the YAML configuration file.
        """

        self.config_path = config_path

    def load_config_file(self) -> ConfigModel:
        """Read the YAML config file and validate it into a ConfigModel.

        Returns:
            config (ConfigModel): The validated configuration.
        """

        with open(self.config_path, encoding="utf-8") as file:
            raw_config = yaml.safe_load(file)

        config = ConfigModel.model_validate(raw_config)

        logger.info("Successfully loaded configuration settings.")

        return config
