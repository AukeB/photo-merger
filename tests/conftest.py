"""Shared pytest fixtures. Test images are generated on the fly, so no sample files are needed."""

from pathlib import Path

import pytest
from PIL import Image

from photo_merger.config_manager import ConfigManager
from photo_merger.config_model import ConfigModel

_EXIF_DATETIME_ORIGINAL = 0x9003
_EXIF_DATETIME = 0x0132


def write_image(
    path: Path,
    datetime_original: str | None = None,
    datetime: str | None = None,
) -> Path:
    """Write a small image, optionally with EXIF date tags.

    Args:
        path (Path): Where to write the image. The extension selects the format.
        datetime_original (str | None): EXIF DateTimeOriginal, such as
            "2024:01:02 10:00:00".
        datetime (str | None): EXIF DateTime tag.

    Returns:
        path (Path): The path the image was written to.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (4, 4), (120, 60, 30))
    exif = Image.Exif()

    if datetime_original is not None:
        exif[_EXIF_DATETIME_ORIGINAL] = datetime_original

    if datetime is not None:
        exif[_EXIF_DATETIME] = datetime

    if len(exif) > 0:
        image.save(path, exif=exif)
    else:
        image.save(path)

    return path


@pytest.fixture(name="config")
def fixture_config() -> ConfigModel:
    """Provide the configuration shipped with the package.

    Returns:
        config (ConfigModel): The validated default configuration.
    """

    config = ConfigManager().load_config_file()

    return config


@pytest.fixture(name="photo_tree")
def fixture_photo_tree(tmp_path: Path) -> Path:
    """Provide a photo tree named "Holiday", with photos at the root and in two folders.

    Args:
        tmp_path (Path): Pytest's per-test temporary folder.

    Returns:
        root (Path): The "Holiday" directory.
    """

    root = tmp_path / "Holiday"
    write_image(root / "IMG_2024-01-01_09-00-00.jpg")
    write_image(root / "day one" / "a.jpg", datetime_original="2024:01:02 10:00:00")
    write_image(root / "day one" / "b.png")
    write_image(root / "day two" / "c.jpg", datetime="2024:01:03 11:00:00")
    (root / "notes.txt").write_text("not a photo")

    return root
