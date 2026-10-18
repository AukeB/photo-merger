# Photo merger

Merge photos from multiple directories chronologically into a single directory by extracting metadata.

## Running

Run the command from the directory that holds the photos:

```bash
uv sync
cd /path/to/Holiday
uv run --project /path/to/photo-merger python /path/to/photo-merger/main.py
```

The merged copies go into a sibling folder named after the current directory, with the
suffix from the configuration. For `Holiday`, that is `Holiday_merged`, next to `Holiday`.
The originals are left untouched.

## How files are named

Each photo is renamed from its capture date, followed by the names of the subfolders it came
from, in lowercase, joined with underscores:

- The date comes from the EXIF metadata (`DateTimeOriginal`, then `DateTime`), or else from a
  `YYYY-MM-DD_HH-MM-SS` pattern in the file name. Without either, the date part is empty.
- Duplicate names get a counter, such as `2024_01_02_day_one_001.jpg`.

## Configuration

`src/photo_merger/configs/config.yaml` sets the file extensions to merge and the suffix of the
merged folder. Unknown keys are rejected.

## Development

```bash
uv run pytest      # tests, with 100% line and branch coverage of src/
uv run ruff check .
```

## Ideas

- Support `.mp4` files, extracting the date the same way as for images.
- Improve date recognition from file names.
- A command-line interface with options for the input and output directories, excluding
  subdirectories, the output name, deleting the originals, verbose output, log export, a dry-run
  mode, and ignoring hidden files and directories.
- A user interface that does the same as the command-line interface.
- Ignore hidden folders such as `.venv`. At the moment they are scanned like any other folder, so
  images inside them are merged too.
- Decide what happens when the merged folder already exists. At the moment files with the same
  name are overwritten, and the verification step fails if the folder holds extra files.
