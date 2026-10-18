"""Tests for the utils module."""

import copy
import logging
from pathlib import Path

import pytest

from photo_merger import utils
from photo_merger.utils import (
    aggregate_sizes_by_subdir_and_extension,
    configure_image_libraries,
    extract_datetime_from_file_name,
    extract_metadata,
    obtain_file_sizes,
    print_aggregated_sizes_table,
)
from tests.conftest import write_image


# Testing the "configure_image_libraries" function.


def test_configure_image_libraries_lifts_the_pixel_limit_and_is_repeatable() -> None:
    configure_image_libraries()
    configure_image_libraries()

    assert utils.Image.MAX_IMAGE_PIXELS is None


# Testing the "extract_metadata" function.


def test_extract_metadata_reads_datetime_original(tmp_path: Path) -> None:
    image_path = write_image(tmp_path / "a.jpg", datetime_original="2024:01:02 10:00:00")

    datetime_str = extract_metadata(file_path=image_path)

    assert datetime_str == "2024_01_02_10_00_00"


def test_extract_metadata_falls_back_to_datetime_tag(tmp_path: Path) -> None:
    image_path = write_image(tmp_path / "a.jpg", datetime="2023:05:06 07:08:09")

    datetime_str = extract_metadata(file_path=image_path)

    assert datetime_str == "2023_05_06_07_08_09"


def test_extract_metadata_returns_none_without_exif(tmp_path: Path) -> None:
    image_path = write_image(tmp_path / "a.png")

    assert extract_metadata(file_path=image_path) is None


def test_extract_metadata_returns_none_for_empty_date_tags(tmp_path: Path) -> None:
    image_path = write_image(tmp_path / "a.jpg", datetime_original="")

    assert extract_metadata(file_path=image_path) is None


def test_extract_metadata_logs_and_returns_none_for_unreadable_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    not_an_image = tmp_path / "broken.jpg"
    not_an_image.write_text("this is not an image")

    with caplog.at_level(logging.ERROR, logger="photo_merger.utils"):
        datetime_str = extract_metadata(file_path=not_an_image)

    assert datetime_str is None
    assert "Failed to read EXIF metadata" in caplog.text


# Testing the "extract_datetime_from_file_name" function.


def test_extract_datetime_from_file_name_finds_the_date() -> None:
    file_path = Path("IMG_2024-01-02_10-00-00.jpg")
    datetime_str = extract_datetime_from_file_name(file_path)

    assert datetime_str == "2024_01_02_10_00_00"


def test_extract_datetime_from_file_name_returns_none_without_a_date() -> None:
    file_path = Path("holiday.jpg")

    assert extract_datetime_from_file_name(file_path) is None


# Testing the "obtain_file_sizes" function.


def test_obtain_file_sizes_reports_megabytes(tmp_path: Path) -> None:
    file_path = tmp_path / "big.bin"
    file_path.write_bytes(b"x" * (1024 * 1024 + 512 * 1024))

    file_sizes = obtain_file_sizes(file_paths=[file_path])

    assert file_sizes == {file_path: 1.5}


def test_obtain_file_sizes_skips_and_logs_missing_files(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "missing.jpg"

    with caplog.at_level(logging.WARNING, logger="photo_merger.utils"):
        file_sizes = obtain_file_sizes(file_paths=[missing])

    assert file_sizes == {}
    assert "Could not get size" in caplog.text


# Testing the "aggregate_sizes_by_subdir_and_extension" function.


def test_aggregate_groups_counts_and_sizes_by_subdir_and_extension(tmp_path: Path) -> None:
    file_size_mapping = {
        tmp_path / "a.JPG": 1.0,
        tmp_path / "day" / "b.jpg": 2.0,
        tmp_path / "day" / "c.jpg": 0.5,
        tmp_path / "day" / "d.png": 3.0,
    }

    aggregated = aggregate_sizes_by_subdir_and_extension(
        file_size_mapping=file_size_mapping,
        root_directory_path=tmp_path,
    )

    assert aggregated[Path(".")][".jpg"] == {"count": 1, "total_size_mb": 1.0}
    assert aggregated[Path("day")][".jpg"] == {"count": 2, "total_size_mb": 2.5}
    assert aggregated[Path("day")][".png"] == {"count": 1, "total_size_mb": 3.0}


# Testing the "print_aggregated_sizes_table" function.


def test_print_aggregated_sizes_table_logs_a_total_row_and_keeps_its_input(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aggregated = {Path("day"): {".jpg": {"count": 2, "total_size_mb": 3.0}}}
    original_copy = copy.deepcopy(aggregated)

    with caplog.at_level(logging.INFO, logger="photo_merger.utils"):
        print_aggregated_sizes_table(aggregated_data=aggregated)

    assert aggregated == original_copy
    assert "Subdirectory" in caplog.text
    assert "TOTAL" in caplog.text
    assert "3.00" in caplog.text


def test_print_aggregated_sizes_table_handles_zero_counts_and_no_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="photo_merger.utils"):
        print_aggregated_sizes_table(aggregated_data={})

        empty_folder = {Path("empty"): {".jpg": {"count": 0, "total_size_mb": 0.0}}}
        print_aggregated_sizes_table(aggregated_data=empty_folder)

    assert caplog.text.count("TOTAL") == 2
