"""Tests for pynamicgain.__main__ CLI utilities."""

import os
import sys
from unittest.mock import patch

import pytest

from pynamicgain.__main__ import _parse_cli_float, _parse_cli_int, backup_seed_csv


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


class TestBackupSeedCsv:
    def test_creates_backup_file(self, sample_toml_dir, capsys):
        with patch("sys.argv", ["pydg_backup_csv", f"--setup_dir={sample_toml_dir}"]):
            backup_seed_csv()
        out = capsys.readouterr().out
        assert "Backup created:" in out
        assert ".bak" in out

        # Verify the .bak file actually exists
        bak_path = out.strip().split("Backup created: ")[1]
        assert os.path.isfile(bak_path)

    def test_missing_setup_dir(self, tmp_path, capsys):
        bad_dir = str(tmp_path / "nonexistent")
        with patch("sys.argv", ["pydg_backup_csv", f"--setup_dir={bad_dir}"]):
            with pytest.raises(SystemExit):
                backup_seed_csv()

    def test_help_flag(self, capsys):
        with patch("sys.argv", ["pydg_backup_csv", "--help"]):
            backup_seed_csv()
        out = capsys.readouterr().out
        assert "Usage:" in out
