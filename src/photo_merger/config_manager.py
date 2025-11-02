"""Module for loading the configuration files."""

import yaml
import logging

from pathlib import Path
from pydantic import BaseModel, ConfigDict

from src.photo_merger.constants import CONFIG_PATH


logger = logging.getLogger(__name__)


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfigModel(ConfiguredBaseModel):
    """Configuration model for photo-merger"""

    allowed_image_extensions: list[str]
    output_directory_name_suffix: str


class ConfigManager:
    """Handles loading and parsing the YAML configuration file."""

    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path

    def load_config_file(self) -> ConfigModel:
        """Loads and validates the YAML config file into a ConfigModel."""
        with open(self.config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        config_model = ConfigModel(**config)

        logger.info("Successfully loaded configuration settings.")

        return config_model
