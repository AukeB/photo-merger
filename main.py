"""Module for running the main repository workflow."""

import yaml
import logging

from pathlib import Path

from src.photo_merger.config_manager import ConfigManager
from src.photo_merger.photo_merger import PhotoMerger


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")



def main():
    # Load configuration manager and settings.
    manager = ConfigManager()
    config = manager.load_config_file()

    root_directory = Path("/home/auke_b/Downloads/2025-10-03 Canada/")

    # Intialise photo merger.
    photo_merger = PhotoMerger(
        root_directory=root_directory,
        config=config
    )

    # Execute main workflow.
    photo_merger.merge()



if __name__ == "__main__":
    main()
