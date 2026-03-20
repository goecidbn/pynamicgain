"""Tests for pynamicgain.config."""

import logging
import os

import pytest
import tomli_w

from pynamicgain._types import SetupConfig
from pynamicgain.config import (
    check_directory,
    config_header,
    load_config,
    read_setup_configs,
    setup_logging,
    validate_setup_configs,
)
from conftest import SAMPLE_TOML_DICT


# -- validate_setup_configs -------------------------------------------------

class TestValidateSetupConfigs:
    def test_valid(self):
        validate_setup_configs(SAMPLE_TOML_DICT)

    def test_missing_key(self):
        bad = {k: v for k, v in SAMPLE_TOML_DICT.items() if k != "version"}
        with pytest.raises(ValueError, match="version"):
            validate_setup_configs(bad)

    def test_wrong_type(self):
        bad = dict(SAMPLE_TOML_DICT, setup_id="not_an_int")
        with pytest.raises(TypeError, match="setup_id"):
            validate_setup_configs(bad)

    def test_setup_id_zero(self):
        bad = dict(SAMPLE_TOML_DICT, setup_id=0)
        with pytest.raises(ValueError, match="setup_id"):
            validate_setup_configs(bad)

    def test_n_seeds_per_setup_zero(self):
        bad = dict(SAMPLE_TOML_DICT, n_seeds_per_setup=0)
        with pytest.raises(ValueError, match="n_seeds_per_setup"):
            validate_setup_configs(bad)

    def test_negative_seed_index(self):
        bad = dict(SAMPLE_TOML_DICT, current_seed_index=-1)
        with pytest.raises(ValueError, match="current_seed_index"):
            validate_setup_configs(bad)


# -- read_setup_configs -----------------------------------------------------

class TestReadSetupConfigs:
    def test_missing_dir(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="does not exist"):
            read_setup_configs(str(tmp_path / "nonexistent"))

    def test_empty_dir(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No setup file"):
            read_setup_configs(str(tmp_path))

    def test_two_setup_files(self, tmp_path):
        for name in ("setup_1.toml", "setup_2.toml"):
            (tmp_path / name).write_bytes(tomli_w.dumps(SAMPLE_TOML_DICT).encode())
        with pytest.raises(ValueError, match="Expected exactly one"):
            read_setup_configs(str(tmp_path))

    def test_valid(self, sample_toml_dir):
        path, cfg = read_setup_configs(str(sample_toml_dir))
        assert os.path.isfile(path)
        assert cfg["setup_id"] == 1

    def test_corrupted_toml(self, tmp_path):
        (tmp_path / "setup_1.toml").write_text("invalid = [unterminated")
        with pytest.raises(ValueError, match="Failed to parse"):
            read_setup_configs(str(tmp_path))


# -- load_config ------------------------------------------------------------

class TestLoadConfig:
    def test_returns_setup_config(self, sample_toml_dir, tmp_path):
        cli_args = {
            "setup_dir": str(sample_toml_dir),
            "out_dir": str(tmp_path / "out"),
            "input_dir": str(tmp_path / "input"),
            "std": 100.0,
            "corr_t": 5.0,
        }
        cfg = load_config(cli_args)
        assert isinstance(cfg, SetupConfig)
        assert cfg.setup_id == 1
        assert cfg.std == 100.0

    def test_cli_overrides_toml(self, sample_toml_dir, tmp_path):
        cli_args = {
            "setup_dir": str(sample_toml_dir),
            "out_dir": str(tmp_path / "out"),
            "input_dir": str(tmp_path / "input"),
            "n_sweeps": 42,
        }
        cfg = load_config(cli_args)
        assert cfg.n_sweeps == 42

    def test_default_backup_dir(self, sample_toml_dir, tmp_path):
        cli_args = {
            "setup_dir": str(sample_toml_dir),
            "out_dir": str(tmp_path / "out"),
            "input_dir": str(tmp_path / "input"),
        }
        cfg = load_config(cli_args)
        assert "backup" in cfg.backup_dir

    def test_default_analysis_dir(self, sample_toml_dir, tmp_path):
        cli_args = {
            "setup_dir": str(sample_toml_dir),
            "out_dir": str(tmp_path / "out"),
            "input_dir": str(tmp_path / "input"),
        }
        cfg = load_config(cli_args)
        assert "analysis" in cfg.analysis_dir


# -- check_directory --------------------------------------------------------

class TestCheckDirectory:
    def test_creates_dir(self, tmp_path):
        new_dir = tmp_path / "subdir" / "nested"
        check_directory(str(new_dir), "test")
        assert os.path.isdir(new_dir)

    def test_existing_dir(self, tmp_path):
        check_directory(str(tmp_path), "test")  # should not raise


# -- config_header ----------------------------------------------------------

class TestConfigHeader:
    def test_contains_setup_id(self):
        header = config_header(SAMPLE_TOML_DICT)
        assert "1" in header

    def test_contains_creator(self):
        header = config_header(SAMPLE_TOML_DICT)
        assert "pytest" in header


# -- setup_logging ----------------------------------------------------------

class TestSetupLogging:
    def test_idempotent(self):
        pkg_logger = logging.getLogger("pynamicgain")
        # Clear any existing handlers from previous tests
        pkg_logger.handlers.clear()
        setup_logging("DEBUG")
        n_handlers = len(pkg_logger.handlers)
        setup_logging("DEBUG")  # second call should be no-op
        assert len(pkg_logger.handlers) == n_handlers
        # Clean up
        pkg_logger.handlers.clear()
