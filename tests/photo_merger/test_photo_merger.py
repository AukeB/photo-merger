"""Tests for the photo_merger module."""

import logging
from pathlib import Path

import pytest

from photo_merger.config_model import ConfigModel
from photo_merger.errors import MergeVerificationError
from photo_merger.photo_merger import PhotoMerger
from tests.conftest import write_image


@pytest.fixture(name="merger")
def fixture_merger(photo_tree: Path, config: ConfigModel) -> PhotoMerger:
    """Provide a merger for the photo tree.

    Args:
        photo_tree (Path): The "Holiday" directory with photos in it.
        config (ConfigModel): The default configuration.

    Returns:
        merger (PhotoMerger): A merger for the tree.
    """

    merger = PhotoMerger(root_directory=photo_tree, config=config)

    return merger


# Testing the "__init__" method from the "PhotoMerger" class.


def test_init_places_the_merged_folder_next_to_the_source(
    merger: PhotoMerger, photo_tree: Path
) -> None:
    assert merger.output_directory_path == photo_tree.parent / "Holiday_merged"
    assert merger.output_directory_path.parent == photo_tree.parent


# Testing the "_is_allowed_file" method from the "PhotoMerger" class.


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [("photo.JPG", True), ("photo.png", True), ("notes.txt", False), ("no_extension", False)],
)
def test_is_allowed_file_compares_lowercase_extensions(
    merger: PhotoMerger, file_name: str, expected: bool
) -> None:
    file_path = Path(file_name)

    assert merger._is_allowed_file(file_path) is expected


# Testing the "_obtain_file_paths" method from the "PhotoMerger" class.


def test_obtain_file_paths_finds_allowed_files_recursively(merger: PhotoMerger) -> None:
    file_paths = merger._obtain_file_paths()

    assert len(file_paths) == 4
    suffixes = [path.suffix.lower() for path in file_paths]

    assert ".txt" not in suffixes


# Testing the "_obtain_datetime_string" method from the "PhotoMerger" class.


def test_obtain_datetime_string_prefers_metadata(merger: PhotoMerger, tmp_path: Path) -> None:
    image_path = write_image(tmp_path / "IMG_2020-01-01_00-00-00.jpg", datetime_original="2024:02:03 04:05:06")

    assert merger._obtain_datetime_string(file_path=image_path) == "2024_02_03_04_05_06"


def test_obtain_datetime_string_uses_file_name_when_metadata_is_missing(
    merger: PhotoMerger, tmp_path: Path
) -> None:
    image_path = write_image(tmp_path / "IMG_2021-07-08_09-10-11.png")

    assert merger._obtain_datetime_string(file_path=image_path) == "2021_07_08_09_10_11"


def test_obtain_datetime_string_falls_back_to_empty_string_with_a_warning(
    merger: PhotoMerger, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    image_path = write_image(tmp_path / "holiday.png")

    with caplog.at_level(logging.WARNING, logger="photo_merger.photo_merger"):
        datetime_str = merger._obtain_datetime_string(file_path=image_path)

    assert datetime_str == ""
    assert "No datetime found" in caplog.text


# Testing the "_build_new_file_name" method from the "PhotoMerger" class.


def test_build_new_file_name_for_a_root_file_uses_only_the_date(
    merger: PhotoMerger, photo_tree: Path
) -> None:
    new_name = merger._build_new_file_name(
        file_path=photo_tree / "IMG.JPG", datetime_str="2024_01_01"
    )

    assert new_name == "2024_01_01.jpg"


def test_build_new_file_name_includes_lowercased_subdirectory_names(
    merger: PhotoMerger, photo_tree: Path
) -> None:
    new_name = merger._build_new_file_name(
        file_path=photo_tree / "day one" / "a.PNG", datetime_str="2024_01_02"
    )

    assert new_name == "2024_01_02_day_one.png"


# Testing the "_generate_new_file_names" method from the "PhotoMerger" class.


def test_generate_new_file_names_maps_every_file(merger: PhotoMerger) -> None:
    file_paths = merger._obtain_file_paths()

    mapping = merger._generate_new_file_names(file_paths=file_paths)

    assert set(mapping) == set(file_paths)


# Testing the "_resolve_duplicate_output_file_names" method from the "PhotoMerger" class.


def test_resolve_duplicate_output_file_names_adds_counters(merger: PhotoMerger) -> None:
    first = Path("a.jpg")
    second = Path("b.jpg")
    third = Path("c.png")

    resolved = merger._resolve_duplicate_output_file_names(
        file_renaming_mapping={first: "2024.jpg", second: "2024.jpg", third: "2025.png"}
    )

    assert resolved == {first: "2024.jpg", second: "2024_001.jpg", third: "2025.png"}


# Testing the "_analyze_and_print_file_sizes" method from the "PhotoMerger" class.


def test_analyze_and_print_file_sizes_logs_a_table(
    merger: PhotoMerger, caplog: pytest.LogCaptureFixture
) -> None:
    file_paths = merger._obtain_file_paths()

    with caplog.at_level(logging.INFO, logger="photo_merger.utils"):
        merger._analyze_and_print_file_sizes(file_paths=file_paths)

    assert "TOTAL" in caplog.text


# Testing the "_copy_and_rename_files" method from the "PhotoMerger" class.


def test_copy_and_rename_files_creates_the_merged_folder(merger: PhotoMerger) -> None:
    file_paths = merger._obtain_file_paths()
    mapping = {path: f"copy_{index}{path.suffix.lower()}" for index, path in enumerate(file_paths)}

    merger._copy_and_rename_files(file_renaming_mapping=mapping)

    copied_entries = merger.output_directory_path.iterdir()
    copied_names = [p.name for p in copied_entries]
    mapped_names = mapping.values()
    expected_names = sorted(mapped_names)

    copied_sorted = sorted(copied_names)

    assert copied_sorted == expected_names


# Testing the "_count_allowed_files_in" method from the "PhotoMerger" class.


def test_count_allowed_files_in_ignores_subdirectories_and_other_files(
    merger: PhotoMerger, photo_tree: Path
) -> None:
    assert merger._count_allowed_files_in(photo_tree) == 1
    assert merger._count_allowed_files_in(photo_tree / "day one") == 2


# Testing the "_count_original_files" method from the "PhotoMerger" class.


def test_count_original_files_totals_every_folder(merger: PhotoMerger) -> None:
    assert merger._count_original_files() == 4


def test_count_original_files_skips_folders_without_photos(
    config: ConfigModel, tmp_path: Path
) -> None:
    root = tmp_path / "Empty"
    (root / "no_photos_here").mkdir(parents=True)
    (root / "readme.txt").write_text("nothing to merge")
    merger = PhotoMerger(root_directory=root, config=config)

    assert merger._count_original_files() == 0


# Testing the "_verify_merge" method from the "PhotoMerger" class.


def test_verify_merge_passes_when_counts_match(
    merger: PhotoMerger, caplog: pytest.LogCaptureFixture
) -> None:
    merger.merge()

    with caplog.at_level(logging.INFO, logger="photo_merger.photo_merger"):
        merger._verify_merge()

    assert "verification passed" in caplog.text


def test_verify_merge_raises_when_a_file_is_missing(merger: PhotoMerger) -> None:
    merger.merge()
    entries = merger.output_directory_path.iterdir()
    first_entry = next(entries)
    first_entry.unlink()

    with pytest.raises(MergeVerificationError) as error:
        merger._verify_merge()

    assert error.value.original_count == 4
    assert error.value.merged_count == 3


# Testing the "merge" method from the "PhotoMerger" class.


def test_merge_copies_everything_into_the_sibling_folder(
    merger: PhotoMerger, photo_tree: Path
) -> None:
    merger.merge()

    merged_entries = merger.output_directory_path.iterdir()
    merged_names = sorted(p.name for p in merged_entries)

    assert merged_names == [
        "2024_01_01_09_00_00.jpg",
        "2024_01_02_10_00_00_day_one.jpg",
        "2024_01_03_11_00_00_day_two.jpg",
        "_day_one.png",
    ]

    assert (photo_tree.parent / "Holiday_merged").is_dir()
    assert not (photo_tree / "Holiday_merged").exists()
