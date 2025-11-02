"""Module that defines the PhotoMerger class responsible for image file collection."""

import re
import shutil
import logging

from tqdm import tqdm
from pathlib import Path
from PIL import Image, ExifTags

from src.photo_merger.config_manager import ConfigModel


Image.MAX_IMAGE_PIXELS = None
logger = logging.getLogger(__name__)


class PhotoMerger:
    """
    Handles image collection and filtering based on allowed file extensions.

    Attributes:
        root_directory (Path): Root directory to search for images.
        allowed_image_extensions (list[str]): List of valid image file extensions.
    """

    def __init__(self, root_directory: Path, config: ConfigModel) -> None:
        """
        Initializes the PhotoMerger with the given directory and configuration.

        Args:
            root_directory (Path): Path to the root directory containing subfolders.
            config (ConfigModel): Configuration model containing allowed extensions.
        """
        self.root_directory = root_directory
        self.allowed_image_extensions: list[str] = config.allowed_image_extensions
        self.output_directory_path = (
            root_directory.parent
            / f"{root_directory.name}{config.output_directory_name_suffix}"
        )

    def _obtain_image_file_paths(self) -> list[Path]:
        """
        Recursively searches for image files with allowed extensions.

        Returns:
            list[Path]: List of valid image file paths found within all subdirectories.
        """
        image_file_paths = [
            path
            for path in self.root_directory.rglob("*")
            if path.suffix.lower() in self.allowed_image_extensions
        ]

        logger.info("✅ Found %d image files.", len(image_file_paths))
        return image_file_paths

    def _extract_metadata(self, image_path: Path) -> str | None:
        """
        Extracts the EXIF 'DateTime' or 'DateTimeOriginal' from an image.

        Args:
            image_path (Path): Path to the image file.

        Returns:
            str | None: Formatted datetime string (YYYY_MM_DD_HH_MM_SS) or None.
        """
        try:
            with Image.open(image_path) as img:
                exif_data = img.getexif()

                if not exif_data:
                    return None

                readable_tags = {
                    ExifTags.TAGS.get(tag_id, tag_id): value
                    for tag_id, value in exif_data.items()
                }

                datetime_str = readable_tags.get(
                    "DateTimeOriginal"
                ) or readable_tags.get("DateTime")

                if not datetime_str:
                    return None

                formatted_datetime = datetime_str.replace(":", "_").replace(" ", "_")
                return formatted_datetime

        except Exception as e:
            logger.error("❌ Failed to read EXIF metadata from %s: %s", image_path, e)
            return None

    def _extract_datetime_from_file_name(self, image_path: Path) -> str | None:
        """
        Extracts a datetime from the filename and formats it as a string.

        Args:
            image_path (Path): Path to the image file.

        Returns:
            str | None: Formatted datetime string (YYYY_MM_DD_HH_MM_SS) or None.
        """
        pattern = r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})"
        match = re.search(pattern, image_path.name)

        if not match:
            return None

        formatted_datetime = match.group(1).replace("-", "_")
        return formatted_datetime

    def _generate_new_file_names(self, image_file_paths: list[Path]) -> dict[Path, str]:
        """
        Generates new filenames for each image based on datetime and subdirectories.

        Args:
            image_file_paths (list[Path]): List of image paths to generate filenames for.

        Returns:
            dict[Path, str]: Mapping from original Path to new filename string. Format:
                datetime_subdir1_subdir2_..._extension.
        """
        image_rename_mapping: dict[Path, str] = {}

        for img_file_path in image_file_paths:
            # First obtain datetime from metadata or filename.
            datetime_str = self._extract_metadata(image_path=img_file_path)

            if not datetime_str:
                datetime_str = self._extract_datetime_from_file_name(
                    image_path=img_file_path
                )

            if not datetime_str:
                logger.warning(
                    "⚠️ No datetime found for image %s; using empty string as fallback.",
                    img_file_path,
                )
                datetime_str = ""

            # Then obtain subdirectory names to append to filename.
            relative_path = img_file_path.parent.relative_to(self.root_directory)
            subdirs_formatted = "_".join(
                part.lower().replace(" ", "_") for part in relative_path.parts
            )
            ext = img_file_path.suffix.lower()

            # Combine datetime, s ubdirectories, and extension into new filename.
            if subdirs_formatted:
                new_file_name = f"{datetime_str}_{subdirs_formatted}{ext}"
            else:
                new_file_name = f"{datetime_str}{ext}"

            image_rename_mapping[img_file_path] = new_file_name

        return image_rename_mapping

    def _resolve_duplicate_output_file_paths(
        self, image_rename_mapping: dict[Path, str]
    ) -> dict[Path, str]:
        """
        Ensures all output filenames are unique by appending a counter to duplicates.

        Args:
            image_rename_mapping (dict[Path, str]): Mapping from original Path to proposed new
                filename.

        Returns:
            dict[Path, str]: Updated mapping with all filenames unique.
        """
        new_mapping: dict[Path, str] = {}
        file_name_counts: dict[str, int] = {}

        for original_path, new_file_name in image_rename_mapping.items():
            count = file_name_counts.get(new_file_name, 0)

            if count > 0:
                name, ext = new_file_name.rsplit(".", 1)
                new_file_name = f"{name}_{count:03}.{ext}"

            new_mapping[original_path] = new_file_name
            file_name_counts[image_rename_mapping[original_path]] = count + 1

        return new_mapping

    def _copy_and_rename_images(self, image_rename_mapping: dict[Path, str]) -> None:
        """
        Copies images to the merged output folder using new filenames.
        """
        self.output_directory_path.mkdir(exist_ok=True)

        for original_path, new_file_name in tqdm(
            image_rename_mapping.items(),
            total=len(image_rename_mapping),
            desc="Copying images",
            unit=" image",
        ):
            new_path = self.output_directory_path / new_file_name
            shutil.copy2(original_path, new_path)

        logger.info(
            "✅ Copied and renamed %d images to %s",
            len(image_rename_mapping),
            self.output_directory_path,
        )

    def _verify_merge(self) -> None:
        """
        Verifies that all images were copied to the merged folder correctly.

        Prints the number of images per subdirectory, total images in all subdirs,
        and the total number of images in the merged directory. Asserts equality.
        """
        logger.info("=== Image count per subdirectory ===")
        total_original = 0
        for subdir in self.root_directory.rglob("*"):
            if subdir.is_dir():
                count = sum(
                    1
                    for path in subdir.iterdir()
                    if path.suffix.lower() in self.allowed_image_extensions
                )
                if count > 0:
                    logger.info(f"{subdir.relative_to(self.root_directory)}: {count}")
                    total_original += count

        # Include images directly in the root directory
        root_count = sum(
            1
            for path in self.root_directory.iterdir()
            if path.is_file() and path.suffix.lower() in self.allowed_image_extensions
        )
        if root_count > 0:
            logger.info(f"(root): {root_count}")
            total_original += root_count

        logger.info(f"Total images in all subdirectories: {total_original}")

        # Count images in the merged directory
        total_merged = sum(
            1
            for path in self.output_directory_path.iterdir()
            if path.is_file() and path.suffix.lower() in self.allowed_image_extensions
        )
        logger.info(f"Total images in merged directory: {total_merged}")

        # Assert equality
        assert total_original == total_merged, (
            "❌ Mismatch between original and merged image counts"
        )

        logger.info("✅ Merge verification passed: all images copied successfully.")

    def merge(self) -> None:
        """ """
        image_file_paths = self._obtain_image_file_paths()

        image_rename_mapping: dict[Path, str] = self._generate_new_file_names(
            image_file_paths=image_file_paths
        )

        image_rename_mapping = self._resolve_duplicate_output_file_paths(
            image_rename_mapping=image_rename_mapping
        )

        self._copy_and_rename_images(image_rename_mapping=image_rename_mapping)

        self._verify_merge()
