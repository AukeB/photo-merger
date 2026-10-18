"""Module for custom exceptions raised by photo-merger."""


class MergeVerificationError(RuntimeError):
    """Raised when the merged directory does not contain every original file.

    Attributes:
        original_count (int): Number of allowed files found in the source tree.
        merged_count (int): Number of allowed files found in the merged directory.
    """

    def __init__(self, original_count: int, merged_count: int) -> None:
        """Record the two counts that did not match.

        Args:
            original_count (int): Number of allowed files found in the source tree.
            merged_count (int): Number of allowed files found in the merged directory.
        """

        super().__init__(
            f"Mismatch between original ({original_count}) and merged "
            f"({merged_count}) file counts."
        )

        self.original_count = original_count
        self.merged_count = merged_count
