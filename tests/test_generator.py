"""Tests for pynamicgain.generator.PyDG."""

import dataclasses
from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pynamicgain._types import SetupConfig
from pynamicgain.generator import PyDG


class TestPyDGInit:
    def test_init_with_config(self, sample_setup_config):
        with patch("pynamicgain.generator.SeedManager") as MockSM:
            MockSM.return_value = MagicMock(current_index=0)
            gen = PyDG(sample_setup_config)
        assert gen.config is sample_setup_config

    def test_init_with_legacy_dict(self, sample_toml_dir, tmp_path):
        cli_args = {
            "setup_dir": str(sample_toml_dir),
            "out_dir": str(tmp_path / "out"),
            "input_dir": str(tmp_path / "input"),
            "std": 100.0,
            "corr_t": 5.0,
        }
        with patch("pynamicgain.generator.SeedManager") as MockSM:
            MockSM.return_value = MagicMock(current_index=0)
            gen = PyDG(cli_args)
        assert isinstance(gen.config, SetupConfig)

    def test_backwards_compat_attrs(self, sample_setup_config):
        with patch("pynamicgain.generator.SeedManager") as MockSM:
            MockSM.return_value = MagicMock(current_index=0)
            gen = PyDG(sample_setup_config)
        assert gen.n_sweeps == sample_setup_config.n_sweeps
        assert gen.sampling_rate == sample_setup_config.sampling_rate


class TestCreateInputAbf:
    @patch("pynamicgain.generator.writeABF1")
    @patch("pynamicgain.generator.generate_input_from_params")
    def test_creates_abf(
        self, mock_gen_input, mock_write, sample_setup_config,
    ):
        # generate_input_from_params returns a fake sweep array
        n_samples = int(
            sample_setup_config.duration * sample_setup_config.sampling_rate
        )
        mock_gen_input.return_value = np.zeros(n_samples)

        gen = PyDG(sample_setup_config)
        result = gen.create_input_abf()

        assert isinstance(result, datetime)
        # writeABF1 called twice (primary + backup)
        assert mock_write.call_count == 2
        # Check array shape passed to writeABF1
        first_call_args = mock_write.call_args_list[0]
        array_arg = first_call_args[0][0]
        assert array_arg.shape == (sample_setup_config.n_sweeps, n_samples)

    @patch("pynamicgain.generator.writeABF1")
    @patch("pynamicgain.generator.generate_input_from_params")
    def test_commits_seeds(
        self, mock_gen_input, mock_write, sample_setup_config,
    ):
        n_samples = int(
            sample_setup_config.duration * sample_setup_config.sampling_rate
        )
        mock_gen_input.return_value = np.zeros(n_samples)

        gen = PyDG(sample_setup_config)
        # Spy on commit
        original_commit = gen.seed_manager.commit
        commit_calls = []

        def spy_commit(records):
            commit_calls.append(records)
            return original_commit(records)

        gen.seed_manager.commit = spy_commit
        gen.create_input_abf()

        assert len(commit_calls) == 1
        assert len(commit_calls[0]) == sample_setup_config.n_sweeps


class TestReturnSetupConfigs:
    def test_returns_dict(self, sample_setup_config):
        with patch("pynamicgain.generator.SeedManager") as MockSM:
            MockSM.return_value = MagicMock(current_index=0)
            gen = PyDG(sample_setup_config)
        d = gen.return_setup_configs_from_attr()
        assert isinstance(d, dict)
        assert "setup_dir" not in d
        assert "setup_file" not in d
        assert "seed_csv" not in d
