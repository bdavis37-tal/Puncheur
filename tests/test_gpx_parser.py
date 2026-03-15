"""Tests for the GPX file parser."""

import pytest

from puncheur.parsers.gpx_parser import parse_gpx


class TestGpxParserErrors:
    """Tests for GPX parser error handling."""

    def test_missing_file(self):
        """Non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_gpx("/nonexistent/file.gpx")
