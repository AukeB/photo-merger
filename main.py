"""Entry point for photo-merger. Merges the photos of the current directory tree."""

import logging
from pathlib import Path

from photo_merger.config_manager import ConfigManager
from photo_merger.photo_merger import PhotoMerger


def main() -> None:
    """Load the configuration and merge the current directory into a sibling folder."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = ConfigManager().load_config_file()
    photo_merger = PhotoMerger(root_directory=Path.cwd(), config=config)
    photo_merger.merge()


if __name__ == "__main__":
    main()
