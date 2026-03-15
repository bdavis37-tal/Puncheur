"""Tests for the FIT file parser.

Note: These tests use synthetic data rather than real FIT files.
The FIT parser integration is tested via the data model layer.
"""

import pytest

from puncheur.parsers.fit_parser import SEMICIRCLE_TO_DEGREES, _semicircles_to_degrees


class TestSemicircleConversion:
    """Tests for FIT file coordinate conversion."""

    def test_positive_latitude(self):
        """Convert positive latitude from semicircles."""
        # 35.1234 degrees in semicircles
        semicircles = int(35.1234 / SEMICIRCLE_TO_DEGREES)
        result = _semicircles_to_degrees(semicircles)
        assert abs(result - 35.1234) < 0.0001

    def test_negative_longitude(self):
        """Convert negative longitude from semicircles."""
        semicircles = int(-80.8765 / SEMICIRCLE_TO_DEGREES)
        result = _semicircles_to_degrees(semicircles)
        assert abs(result - (-80.8765)) < 0.0001

    def test_none_returns_none(self):
        """None input should return None."""
        assert _semicircles_to_degrees(None) is None

    def test_zero(self):
        """Zero semicircles should be zero degrees."""
        assert _semicircles_to_degrees(0) == 0.0


class TestFitParserErrors:
    """Tests for FIT parser error handling."""

    def test_missing_file(self):
        """Non-existent file should raise FileNotFoundError."""
        from puncheur.parsers.fit_parser import parse_fit

        with pytest.raises(FileNotFoundError):
            parse_fit("/nonexistent/file.fit")
