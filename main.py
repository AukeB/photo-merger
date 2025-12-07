"""Module for running the main repository workflow."""

import yaml
import logging

from pathlib import Path

from src.photo_merger.config_manager import ConfigManager
from src.photo_merger.photo_merger import PhotoMerger

from src.photo_merger.config_manager import ConfigManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")



def main():
    # Load configuration manager and settings.
    manager = ConfigManager()
    config = manager.load_config_file()

    root_directory = Path("")

    # Intialise photo merger.
    photo_merger = PhotoMerger(
        root_directory=root_directory,
        config=config
    )

    # Execute main workflow.
    photo_merger.merge()



if __name__ == "__main__":
    main()



"""
TODO

- Overview file types and file size                                                             DONE
- File extension .mp4 support (can we extract datetime similarly as images?)                    TO DO NEXT
- Improved date(time) recogniztion from filename.                                               TO DO NEXT
- CLI Implementation. Parameters
    - input_directory (defaults to current working directory)
    - exlude_sub_directories (defaults to none)
    - output_directory_name (defaults to current working directory name + '_merged')
    - delete_original_directory (defaults to True)
    - verbose to determine to print things or not (defaults to True)
    - export_verbose_to_txt (to create logs of code execution) (defaults to False)
    - dry_run mode (defaults to False)
    --ignore-hidden (defaults to True) (Skip hidden files and directories)

For packaging
- Proper unit testing
- README example usage, configuration settings
- A User interface that does the same as the CLI

"""