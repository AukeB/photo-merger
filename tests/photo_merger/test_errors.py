"""Tests for the errors module."""

from photo_merger.errors import MergeVerificationError


# Testing the "__init__" method from the "MergeVerificationError" class.


def test_merge_verification_error_reports_both_counts() -> None:
    error = MergeVerificationError(original_count=8, merged_count=4)

    assert error.original_count == 8
    assert error.merged_count == 4
    assert "original (8)" in str(error)
    assert "merged (4)" in str(error)
