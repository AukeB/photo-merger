"""Module with helper functions for dates, file sizes and the summary table."""

import logging
import re
from pathlib import Path
from typing import TypedDict

from PIL import ExifTags, Image
from pillow_heif import register_heif_opener

logger = logging.getLogger(__name__)

_FILE_NAME_DATETIME_PATTERN = r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})"
_BYTES_PER_MEGABYTE = 1024**2
_TABLE_HEADERS = [
    "Subdirectory",
    "Extension",
    "Count",
    "Total Size (MB)",
    "Avg Size (MB)",
]


class ExtensionStatistics(TypedDict):
    """Count and total size of the files with one extension in one subdirectory.

    Attributes:
        count (int): Number of files.
        total_size_mb (float): Combined size of the files, in megabytes.
    """

    count: int
    total_size_mb: float


def configure_image_libraries() -> None:
    """Allow very large images and register the HEIC opener with Pillow.

    Both settings are process-wide, so they are applied by the code that needs them
    rather than when this module is imported. Calling this more than once is safe.
    """

    Image.MAX_IMAGE_PIXELS = None
    register_heif_opener()


def extract_metadata(file_path: Path) -> str | None:
    """Read the capture date from the EXIF metadata of an image.

    Args:
        file_path (Path): The image to read.

    Returns:
        formatted_datetime (str | None): The date as "YYYY_MM_DD_HH_MM_SS", or None if
            the image has no date or cannot be read.
    """

    try:
        with Image.open(file_path) as image:
            exif_data = image.getexif()

            if not exif_data:
                return None

            readable_tags = {
                ExifTags.TAGS.get(tag_id, tag_id): value
                for tag_id, value in exif_data.items()
            }

            datetime_str = readable_tags.get("DateTimeOriginal") or readable_tags.get(
                "DateTime"
            )

            if not datetime_str:
                return None

            formatted_datetime = datetime_str.replace(":", "_").replace(" ", "_")

            return formatted_datetime

    except Exception as error:
        logger.error("❌ Failed to read EXIF metadata from %s: %s", file_path, error)

        return None


def extract_datetime_from_file_name(file_path: Path) -> str | None:
    """Find a date in the file name, in the form "YYYY-MM-DD_HH-MM-SS".

    Args:
        file_path (Path): The file whose name is searched.

    Returns:
        formatted_datetime (str | None): The date as "YYYY_MM_DD_HH_MM_SS", or None if
            the name contains no date.
    """

    match = re.search(_FILE_NAME_DATETIME_PATTERN, file_path.name)

    if not match:
        return None

    matched_text = match.group(1)
    formatted_datetime = matched_text.replace("-", "_")

    return formatted_datetime


def obtain_file_sizes(
    file_paths: list[Path],
    rounding_number_of_decimals: int = 2,
) -> dict[Path, float]:
    """Measure the size of each file in megabytes.

    Files that cannot be read are logged and left out of the result.

    Args:
        file_paths (list[Path]): The files to measure.
        rounding_number_of_decimals (int): Decimal places to round the sizes to.

    Returns:
        file_size_mapping (dict[Path, float]): The size of each readable file, in
            megabytes.
    """

    file_size_mapping: dict[Path, float] = {}

    for file_path in file_paths:
        try:
            size_in_bytes = file_path.stat().st_size

            file_size = round(
                size_in_bytes / _BYTES_PER_MEGABYTE, rounding_number_of_decimals
            )

            file_size_mapping[file_path] = file_size

        except OSError as error:
            logger.warning("⚠️ Could not get size for %s (%s)", file_path, error)

    return file_size_mapping


def aggregate_sizes_by_subdir_and_extension(
    file_size_mapping: dict[Path, float],
    root_directory_path: Path,
) -> dict[Path, dict[str, ExtensionStatistics]]:
    """Group file sizes by subdirectory and extension.

    Args:
        file_size_mapping (dict[Path, float]): The size of each file, in megabytes.
        root_directory_path (Path): The directory the subdirectories are relative to.

    Returns:
        aggregated_data (dict[Path, dict[str, ExtensionStatistics]]): For each
            subdirectory, the count and total size of each lowercase extension.
    """

    aggregated_data: dict[Path, dict[str, ExtensionStatistics]] = {}

    for file_path, size_mb in file_size_mapping.items():
        subdir = file_path.parent.relative_to(root_directory_path)
        extension = file_path.suffix.lower()

        subdir_statistics = aggregated_data.setdefault(subdir, {})

        empty_statistics = ExtensionStatistics(count=0, total_size_mb=0.0)
        extension_statistics = subdir_statistics.setdefault(extension, empty_statistics)

        extension_statistics["count"] += 1
        extension_statistics["total_size_mb"] += size_mb

    return aggregated_data


def _build_table_rows(
    aggregated_data: dict[Path, dict[str, ExtensionStatistics]],
) -> list[list[str]]:
    """Turn the aggregated statistics into table rows, followed by a total row.

    Args:
        aggregated_data (dict[Path, dict[str, ExtensionStatistics]]): The statistics to
            show.

    Returns:
        rows (list[list[str]]): One row per subdirectory and extension, then a TOTAL
            row. The subdirectory is only shown on the first row of its group.
    """

    rows: list[list[str]] = []
    total_count = 0
    total_size = 0.0

    for subdir, extension_statistics in aggregated_data.items():
        subdir_text = str(subdir)

        extension_items = extension_statistics.items()

        for index, (extension, statistics) in enumerate(extension_items):
            count = statistics["count"]
            size = statistics["total_size_mb"]
            average_size = size / count if count > 0 else 0.0
            first_row_text = subdir_text if index == 0 else ""

            row = [
                first_row_text,
                extension,
                str(count),
                f"{size:.2f}",
                f"{average_size:.2f}",
            ]

            rows.append(row)

            total_count += count
            total_size += size

    total_average = total_size / total_count if total_count > 0 else 0.0

    total_row = [
        "TOTAL",
        "-",
        str(total_count),
        f"{total_size:.2f}",
        f"{total_average:.2f}",
    ]

    rows.append(total_row)

    return rows


def _render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Lay out headers and rows as aligned text lines.

    Args:
        headers (list[str]): The column titles.
        rows (list[list[str]]): The cell text of each row.

    Returns:
        lines (list[str]): The header, a separator, then one line per row.
    """

    column_widths = [len(header) for header in headers]

    for row in rows:
        for column_index, cell in enumerate(row):
            current_width = column_widths[column_index]
            cell_width = len(cell)
            column_widths[column_index] = max(current_width, cell_width)

    lines: list[str] = []

    header_cells = [
        header.ljust(width) for header, width in zip(headers, column_widths)
    ]

    header_line = "  ".join(header_cells)
    lines.append(header_line)
    header_length = len(header_line)
    lines.append("-" * header_length)

    for row in rows:
        row_cells = [cell.ljust(width) for cell, width in zip(row, column_widths)]
        row_line = "  ".join(row_cells)
        trimmed_line = row_line.rstrip()
        lines.append(trimmed_line)

    return lines


def print_aggregated_sizes_table(
    aggregated_data: dict[Path, dict[str, ExtensionStatistics]],
) -> None:
    """Log the file statistics as an aligned table, with a total row.

    The input is not changed.

    Args:
        aggregated_data (dict[Path, dict[str, ExtensionStatistics]]): The statistics to
            show, from aggregate_sizes_by_subdir_and_extension.
    """

    rows = _build_table_rows(aggregated_data=aggregated_data)
    lines = _render_table(headers=_TABLE_HEADERS, rows=rows)

    for line in lines:
        logger.info(line)
