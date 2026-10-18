"""Module for the configuration schema of photo-merger."""

from pydantic import BaseModel, ConfigDict


class ConfiguredBaseModel(BaseModel):
    """Config that disallows extra parameters not explicitly defined."""

    model_config = ConfigDict(extra="forbid")


class ConfigModel(ConfiguredBaseModel):
    """Config that combines all parameters.

    Attributes:
        output_directory_name_suffix (str): Suffix appended to the source folder name to
            name the merged folder, such as "_merged".
        allowed_file_extensions (list[str]): Lowercase extensions, including the dot, of
            the files to merge.
    """

    output_directory_name_suffix: str
    allowed_file_extensions: list[str]
