"""Module with utility functions."""

import re
import logging

from pathlib import Path
from typing import DefaultDict
from collections import defaultdict
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)


# Functions for obtain datetime, either by extracting metadata or detecting it in filename.


def extract_metadata(file_path: Path) -> str | None:
    """ """
    try:
        with Image.open(file_path) as img:
            exif_data = img.getexif()

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

    except Exception as e:
        logger.error("❌ Failed to read EXIF metadata from %s: %s", file_path, e)
        return None


def extract_datetime_from_file_name(file_path: Path) -> str | None:
    """ """
    pattern = r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})"
    match = re.search(pattern, file_path.name)

    if not match:
        return None

    formatted_datetime = match.group(1).replace("-", "_")
    return formatted_datetime


# Functions for printing file statistics, such as file sizes and counts per subdirectory.


def obtain_file_sizes(
    file_paths: list[Path],
    megabyte_scaling_factor: int = 1024**2,
    rounding_number_of_decimals: int = 2,
) -> dict[Path, float]:
    """ """
    file_size_mapping: dict[Path, float] = {}

    for file_path in file_paths:
        try:
            # Obtain file size in megabytes rounded to 2 digits.
            file_size = round(
                file_path.stat().st_size / megabyte_scaling_factor,
                rounding_number_of_decimals,
            )
            file_size_mapping[file_path] = file_size
        except (OSError, FileNotFoundError) as e:
            logger.warning("⚠️ Could not get size for %s (%s)", file_path, e)

    return file_size_mapping


def aggregate_sizes_by_subdir_and_extension(
    file_size_mapping: dict[Path, float],
    root_directory_path: Path,
    column_name_file_size: str = "total_size_mb",
    column_name_file_count: str = "count",
) -> dict[Path, dict[str, dict[str, float | int]]]:
    """ """
    aggregation: DefaultDict = defaultdict(
        lambda: defaultdict(
            lambda: {column_name_file_size: 0.0, column_name_file_count: 0}
        )
    )

    for file_path, size_mb in file_size_mapping.items():
        subdir = file_path.parent.relative_to(root_directory_path)
        ext = file_path.suffix.lower()
        aggregation[subdir][ext][column_name_file_size] += size_mb
        aggregation[subdir][ext][column_name_file_count] += 1

    aggregated_data = {subdir: dict(ext_map) for subdir, ext_map in aggregation.items()}

    return aggregated_data


def print_aggregated_sizes_table(
    aggregated_data: dict,
) -> None:
    """
    Prints the aggregated file statistics in an aligned table format,
    including a total row computed and appended to the data.
    """
    headers = ["Subdirectory", "Extension", "Count", "Total Size (MB)", "Avg Size (MB)"]
    col_widths = [len(h) for h in headers]

    total_count = 0
    total_size = 0.0

    for subdir, file_types in aggregated_data.items():
        subdir_str = str(subdir)
        col_widths[0] = max(col_widths[0], len(subdir_str))
        for ext, info in file_types.items():
            count = info["count"]
            size = info["total_size_mb"]
            avg_size = size / count if count > 0 else 0.0

            total_count += count
            total_size += size

            col_widths[1] = max(col_widths[1], len(ext))
            col_widths[2] = max(col_widths[2], len(str(count)))
            col_widths[3] = max(col_widths[3], len(f"{size:.2f}"))
            col_widths[4] = max(col_widths[4], len(f"{avg_size:.2f}"))

    aggregated_data["TOTAL"] = {
        "-": {"count": total_count, "total_size_mb": total_size}
    }

    header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print("\n" + header_row)
    print("-" * len(header_row))

    for subdir, file_types in aggregated_data.items():
        subdir_str = str(subdir)
        first_row = True
        for ext, info in file_types.items():
            count = info["count"]
            size = info["total_size_mb"]
            avg_size = size / count if count > 0 else 0.0

            row = (
                f"{subdir_str.ljust(col_widths[0]) if first_row else ' ' * col_widths[0]}  "
                f"{ext.ljust(col_widths[1])}  "
                f"{str(count).rjust(col_widths[2])}  "
                f"{size:>{col_widths[3]}.2f}  "
                f"{avg_size:>{col_widths[4]}.2f}"
            )
            print(row)
            first_row = False

    print("")
