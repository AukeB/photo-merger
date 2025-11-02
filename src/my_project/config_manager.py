"""Module for loading the configuration files."""

import yaml

from pathlib import Path
from pydantic import BaseModel, ConfigDict

from src.my_project.constants import CONFIG_PATH


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfigModel(ConfiguredBaseModel):
    """Config that combines all parameters"""

    class ConfigCategory1(ConfiguredBaseModel):
        """Config for category 1 parameters"""

        float_param: float
        str_param: str

    class ConfigCategory2(ConfiguredBaseModel):
        """Config for category 2 parameters"""

        int_param: int
        bool_param: bool
        list_param: list[str]

    config_category_1: ConfigCategory1
    config_category_two: ConfigCategory2


class ConfigManager:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path

    def load_config_file(self) -> ConfigModel:
        with open(self.config_path) as file:
            config = yaml.safe_load(file)

        return ConfigModel(**config)
