"""Tests for pynamicgain.__main__ CLI utilities."""

import sys

import pytest

from pynamicgain.__main__ import _parse_cli_float, _parse_cli_int


class TestParseCliFloat:
    def test_valid(self):
        assert _parse_cli_float("3.14", "test") == 3.14

    def test_integer_string(self):
        assert _parse_cli_float("42", "test") == 42.0

    def test_invalid(self):
        with pytest.raises(SystemExit):
            _parse_cli_float("not_a_number", "test")

    def test_none(self):
        with pytest.raises(SystemExit):
            _parse_cli_float(None, "test")


class TestParseCliInt:
    def test_valid(self):
        assert _parse_cli_int("42", "test") == 42

    def test_invalid(self):
        with pytest.raises(SystemExit):
            _parse_cli_int("3.14", "test")

    def test_none(self):
        with pytest.raises(SystemExit):
            _parse_cli_int(None, "test")

    def test_non_numeric(self):
        with pytest.raises(SystemExit):
            _parse_cli_int("abc", "test")
