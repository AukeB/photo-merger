"""Module for running the main repository workflow."""

import yaml

from src.my_project.config_manager import ConfigManager

def main():
    # Load configuration manager and settings.
    manager = ConfigManager()
    config = manager.load_config_file()

    print("Loaded config:")
    print(yaml.safe_dump(config.model_dump(), sort_keys=False, default_flow_style=False))



if __name__ == "__main__":
    main()
