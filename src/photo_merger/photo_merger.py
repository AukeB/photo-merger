"""Module that defines the PhotoMerger class responsible for image file collection."""

import shutil
import logging

from tqdm import tqdm
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

from src.photo_merger.config_manager import ConfigModel
from src.photo_merger.utils import (
    extract_metadata,
    extract_datetime_from_file_name,
    obtain_file_sizes,
    aggregate_sizes_by_subdir_and_extension,
    print_aggregated_sizes_table,
)

Image.MAX_IMAGE_PIXELS = None
logger = logging.getLogger(__name__)
register_heif_opener()


class PhotoMerger:
    """ """

    def __init__(self, root_directory: Path, config: ConfigModel) -> None:
        """
        Initializes the PhotoMerger with the given directory and configuration.

        Args:
            root_directory (Path): Path to the root directory containing subfolders.
            config (ConfigModel): Configuration model containing allowed extensions.
        """
        self.root_directory = root_directory
        self.allowed_file_extensions: list[str] = config.allowed_file_extensions
        self.output_directory_path = (
            root_directory.parent
            / f"{root_directory.name}{config.output_directory_name_suffix}"
        )

    def _obtain_file_paths(self) -> list[Path]:
        """ """
        all_file_paths = [
            path
            for path in self.root_directory.rglob("*")
            if path.suffix.lower() in self.allowed_file_extensions
        ]

        logger.info("✅ Found %d files.", len(all_file_paths))
        return all_file_paths

    def _generate_new_file_names(self, file_paths: list[Path]) -> dict[Path, str]:
        """ """
        file_renaming_mapping: dict[Path, str] = {}

        for file_path in file_paths:
            # First obtain datetime from metadata or filename.
            datetime_str = extract_metadata(file_path=file_path)

            if not datetime_str:
                datetime_str = extract_datetime_from_file_name(file_path=file_path)

            if not datetime_str:
                logger.warning(
                    "⚠️ No datetime found for file %s; using empty string as fallback.",
                    file_path,
                )
                datetime_str = ""

            # Then obtain subdirectory names to append to filename.
            relative_path = file_path.parent.relative_to(self.root_directory)
            subdirs_formatted = "_".join(
                part.lower().replace(" ", "_") for part in relative_path.parts
            )
            ext = file_path.suffix.lower()

            # Combine datetime, subdirectories, and extension into new filename.
            if subdirs_formatted:
                new_file_name = f"{datetime_str}_{subdirs_formatted}{ext}"
            else:
                new_file_name = f"{datetime_str}{ext}"

            file_renaming_mapping[file_path] = new_file_name

        return file_renaming_mapping

    def _resolve_duplicate_output_file_names(
        self, file_renaming_mapping: dict[Path, str]
    ) -> dict[Path, str]:
        """
        Ensures all output filenames are unique by appending a counter to duplicates.

        Args:
            file_renaming_mapping (dict[Path, str]): Mapping from original Path to proposed new
                filename.

        Returns:
            dict[Path, str]: Updated mapping with all filenames unique.
        """
        new_mapping: dict[Path, str] = {}
        file_name_counts: dict[str, int] = {}

        for original_path, new_file_name in file_renaming_mapping.items():
            count = file_name_counts.get(new_file_name, 0)

            if count > 0:
                name, ext = new_file_name.rsplit(".", 1)
                new_file_name = f"{name}_{count:03}.{ext}"

            new_mapping[original_path] = new_file_name
            file_name_counts[file_renaming_mapping[original_path]] = count + 1

        return new_mapping

    def _analyze_and_print_file_sizes(
        self,
        file_paths: list[Path],
    ) -> None:
        """ """
        file_sizes = obtain_file_sizes(file_paths=file_paths)
        aggregated_data = aggregate_sizes_by_subdir_and_extension(
            file_size_mapping=file_sizes, root_directory_path=self.root_directory
        )
        print_aggregated_sizes_table(aggregated_data=aggregated_data)

    def _copy_and_rename_files(self, file_renaming_mapping: dict[Path, str]) -> None:
        """
        Copies files to the merged output folder using new filenames.
        """
        self.output_directory_path.mkdir(exist_ok=True)

        for original_path, new_file_name in tqdm(
            file_renaming_mapping.items(),
            total=len(file_renaming_mapping),
            desc="Copying files",
            unit=" file",
        ):
            new_path = self.output_directory_path / new_file_name
            shutil.copy2(original_path, new_path)

        logger.info(
            "✅ Copied and renamed %d files to %s",
            len(file_renaming_mapping),
            self.output_directory_path,
        )

    def _verify_merge(self) -> None:
        """ """
        logger.info("=== File count per subdirectory ===")
        total_original = 0
        for subdir in self.root_directory.rglob("*"):
            if subdir.is_dir():
                count = sum(
                    1
                    for path in subdir.iterdir()
                    if path.suffix.lower() in self.allowed_file_extensions
                )
                if count > 0:
                    logger.info(f"{subdir.relative_to(self.root_directory)}: {count}")
                    total_original += count

        # Include files directly in the root directory
        root_count = sum(
            1
            for path in self.root_directory.iterdir()
            if path.is_file() and path.suffix.lower() in self.allowed_file_extensions
        )
        if root_count > 0:
            logger.info(f"(root): {root_count}")
            total_original += root_count

        logger.info(f"Total files in all subdirectories: {total_original}")

        # Count files in the merged directory
        total_merged = sum(
            1
            for path in self.output_directory_path.iterdir()
            if path.is_file() and path.suffix.lower() in self.allowed_file_extensions
        )
        logger.info(f"Total files in merged directory: {total_merged}")

        difference = total_original - total_merged
        logger.info(f"Difference between original and merge directory: {difference}")

        # Assert equality
        assert total_original == total_merged, (
            "❌ Mismatch between original and merged file counts"
        )

        logger.info("✅ Merge verification passed: all files copied successfully.")

    def merge(self) -> None:
        """ """
        all_file_paths: list[Path] = self._obtain_file_paths()

        self._analyze_and_print_file_sizes(file_paths=all_file_paths)

        file_renaming_mapping: dict[Path, str] = self._generate_new_file_names(
            file_paths=all_file_paths
        )

        file_renaming_mapping = self._resolve_duplicate_output_file_names(
            file_renaming_mapping=file_renaming_mapping
        )

        self._copy_and_rename_files(file_renaming_mapping=file_renaming_mapping)

        self._verify_merge()
