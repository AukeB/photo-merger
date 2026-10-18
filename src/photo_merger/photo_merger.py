"""Module for the PhotoMerger class, which merges photos from subdirectories into one."""

import logging
import shutil
from pathlib import Path

from tqdm import tqdm

from photo_merger.config_model import ConfigModel
from photo_merger.errors import MergeVerificationError
from photo_merger.utils import (
    aggregate_sizes_by_subdir_and_extension,
    configure_image_libraries,
    extract_datetime_from_file_name,
    extract_metadata,
    obtain_file_sizes,
    print_aggregated_sizes_table,
)

logger = logging.getLogger(__name__)


class PhotoMerger:
    """Copy every photo in a directory tree into one sibling folder, renamed by date.

    Each file is named after its capture date, followed by the subdirectory names it
    came from, so files from different folders stay distinguishable and sort in time
    order.

    Attributes:
        root_directory (Path): The directory tree to merge.
        allowed_file_extensions (list[str]): Lowercase extensions of the files to merge.
        output_directory_path (Path): The merged folder, a sibling of root_directory.

    Example:
        >>> merger = PhotoMerger(root_directory=Path.cwd(), config=config)
        >>> merger.merge()
    """

    def __init__(self, root_directory: Path, config: ConfigModel) -> None:
        """Set the directory to merge and work out where the merged copy goes.

        Args:
            root_directory (Path): The directory tree to merge. Its name is used to name
                the merged folder.
            config (ConfigModel): The validated configuration model.
        """

        configure_image_libraries()

        self.root_directory = root_directory
        self.allowed_file_extensions = config.allowed_file_extensions

        output_directory_name = (
            f"{root_directory.name}{config.output_directory_name_suffix}"
        )

        self.output_directory_path = root_directory.parent / output_directory_name

    def _is_allowed_file(self, path: Path) -> bool:
        """Check whether a file has one of the extensions to merge.

        Args:
            path (Path): The path to check.

        Returns:
            is_allowed (bool): True if the file's extension is in the allowed list.
        """

        extension = path.suffix.lower()
        is_allowed = extension in self.allowed_file_extensions

        return is_allowed

    def _obtain_file_paths(self) -> list[Path]:
        """Find every allowed file anywhere under the root directory.

        Returns:
            all_file_paths (list[Path]): The matching files, in directory traversal
                order.
        """

        candidate_paths = self.root_directory.rglob("*")
        all_file_paths = [
            path for path in candidate_paths if self._is_allowed_file(path)
        ]

        file_count = len(all_file_paths)
        logger.info("✅ Found %d files.", file_count)

        return all_file_paths

    def _obtain_datetime_string(self, file_path: Path) -> str:
        """Get the capture date of a file, from its metadata or else its name.

        Args:
            file_path (Path): The file to inspect.

        Returns:
            datetime_str (str): The date, or an empty string if none could be found.
        """

        datetime_str = extract_metadata(file_path=file_path)

        if not datetime_str:
            datetime_str = extract_datetime_from_file_name(file_path=file_path)

        if not datetime_str:
            logger.warning(
                "⚠️ No datetime found for file %s; using empty string as fallback.",
                file_path,
            )

            datetime_str = ""

        return datetime_str

    def _build_new_file_name(self, file_path: Path, datetime_str: str) -> str:
        """Combine the date, the subdirectory names and the extension into a file name.

        Args:
            file_path (Path): The original file.
            datetime_str (str): The file's capture date, possibly empty.

        Returns:
            new_file_name (str): For example "2024_01_02_10_00_00_holiday_day1.jpg".
        """

        relative_path = file_path.parent.relative_to(self.root_directory)
        lowercase_parts = [
            part.lower().replace(" ", "_") for part in relative_path.parts
        ]
        subdirs_formatted = "_".join(lowercase_parts)
        extension = file_path.suffix.lower()

        if subdirs_formatted:
            new_file_name = f"{datetime_str}_{subdirs_formatted}{extension}"
        else:
            new_file_name = f"{datetime_str}{extension}"

        return new_file_name

    def _generate_new_file_names(self, file_paths: list[Path]) -> dict[Path, str]:
        """Propose a new file name for every file.

        Args:
            file_paths (list[Path]): The files to rename.

        Returns:
            file_renaming_mapping (dict[Path, str]): The proposed name for each original
                file. The names may still collide.
        """

        file_renaming_mapping: dict[Path, str] = {}

        for file_path in file_paths:
            datetime_str = self._obtain_datetime_string(file_path=file_path)

            new_file_name = self._build_new_file_name(
                file_path=file_path, datetime_str=datetime_str
            )

            file_renaming_mapping[file_path] = new_file_name

        return file_renaming_mapping

    def _resolve_duplicate_output_file_names(
        self, file_renaming_mapping: dict[Path, str]
    ) -> dict[Path, str]:
        """Make every output file name unique by adding a counter to duplicates.

        Args:
            file_renaming_mapping (dict[Path, str]): The proposed name for each original
                file.

        Returns:
            new_mapping (dict[Path, str]): The unique name for each original file.
        """

        new_mapping: dict[Path, str] = {}
        file_name_counts: dict[str, int] = {}

        for original_path, proposed_name in file_renaming_mapping.items():
            count = file_name_counts.get(proposed_name, 0)
            unique_name = proposed_name

            if count > 0:
                stem, extension = proposed_name.rsplit(".", 1)
                unique_name = f"{stem}_{count:03}.{extension}"

            new_mapping[original_path] = unique_name
            file_name_counts[proposed_name] = count + 1

        return new_mapping

    def _analyze_and_print_file_sizes(self, file_paths: list[Path]) -> None:
        """Log the size statistics of the files, as a table.

        Args:
            file_paths (list[Path]): The files to measure.
        """

        file_sizes = obtain_file_sizes(file_paths=file_paths)

        aggregated_data = aggregate_sizes_by_subdir_and_extension(
            file_size_mapping=file_sizes,
            root_directory_path=self.root_directory,
        )

        print_aggregated_sizes_table(aggregated_data=aggregated_data)

    def _copy_and_rename_files(self, file_renaming_mapping: dict[Path, str]) -> None:
        """Copy each file into the merged folder under its new name.

        Args:
            file_renaming_mapping (dict[Path, str]): The unique new name for each
                original file.
        """

        self.output_directory_path.mkdir(exist_ok=True)

        copy_items = file_renaming_mapping.items()
        total_files = len(file_renaming_mapping)

        progress_bar = tqdm(
            copy_items,
            total=total_files,
            desc="Copying files",
            unit=" file",
        )

        for original_path, new_file_name in progress_bar:
            new_path = self.output_directory_path / new_file_name
            shutil.copy2(original_path, new_path)

        logger.info(
            "✅ Copied and renamed %d files to %s",
            total_files,
            self.output_directory_path,
        )

    def _count_allowed_files_in(self, directory: Path) -> int:
        """Count the allowed files directly inside one directory, not its
        subdirectories.

        Args:
            directory (Path): The directory to count in.

        Returns:
            file_count (int): The number of allowed files directly inside it.
        """

        entries = directory.iterdir()

        allowed_entries = [
            path for path in entries if path.is_file() and self._is_allowed_file(path)
        ]

        file_count = len(allowed_entries)

        return file_count

    def _count_original_files(self) -> int:
        """Count the allowed files in the source tree, and log the count per folder.

        Returns:
            total_original (int): The number of allowed files in the source tree.
        """

        logger.info("=== File count per subdirectory ===")
        total_original = 0

        for subdir in self.root_directory.rglob("*"):
            if not subdir.is_dir():
                continue

            count = self._count_allowed_files_in(subdir)

            if count > 0:
                relative_subdir = subdir.relative_to(self.root_directory)
                logger.info(f"{relative_subdir}: {count}")
                total_original += count

        root_count = self._count_allowed_files_in(self.root_directory)

        if root_count > 0:
            logger.info(f"(root): {root_count}")
            total_original += root_count

        logger.info(f"Total files in all subdirectories: {total_original}")

        return total_original

    def _verify_merge(self) -> None:
        """Check that the merged folder holds as many files as the source tree did.

        Raises:
            MergeVerificationError: If the two counts differ.
        """

        total_original = self._count_original_files()
        total_merged = self._count_allowed_files_in(self.output_directory_path)

        logger.info(f"Total files in merged directory: {total_merged}")

        logger.info(
            f"Difference between original and merge directory: {total_original - total_merged}"
        )

        if total_original != total_merged:
            raise MergeVerificationError(
                original_count=total_original, merged_count=total_merged
            )

        logger.info("✅ Merge verification passed: all files copied successfully.")

    def merge(self) -> None:
        """Merge every allowed file under the root directory into the merged folder.

        Steps: find the files, log their sizes, work out unique new names, copy them,
        then verify that no file was lost.

        Raises:
            MergeVerificationError: If the merged folder does not hold every file.
        """

        all_file_paths = self._obtain_file_paths()

        self._analyze_and_print_file_sizes(file_paths=all_file_paths)

        file_renaming_mapping = self._generate_new_file_names(file_paths=all_file_paths)

        file_renaming_mapping = self._resolve_duplicate_output_file_names(
            file_renaming_mapping=file_renaming_mapping
        )

        self._copy_and_rename_files(file_renaming_mapping=file_renaming_mapping)
        self._verify_merge()
