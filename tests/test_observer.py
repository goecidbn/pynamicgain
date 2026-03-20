"""Tests for pynamicgain.observer.PyDGAnalysis."""

import warnings
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pynamicgain._types import SetupConfig
from pynamicgain.observer import PyDGAnalysis


class TestPyDGAnalysisInit:
    def test_init_with_config(self, sample_setup_config):
        obs = PyDGAnalysis(sample_setup_config)
        assert obs.config is sample_setup_config
        assert len(obs.sweeps2analyse) == sample_setup_config.n_sweeps

    def test_builds_analysis_params(self, sample_setup_config):
        obs = PyDGAnalysis(sample_setup_config)
        assert obs._analysis_params.sampling_rate == 20000
        assert obs._analysis_params.min_spike_height == -5

    def test_builds_vis_params(self, sample_setup_config):
        obs = PyDGAnalysis(sample_setup_config)
        assert obs._vis_params is not None
        assert obs._vis_params.trace_duration == 20


class TestAnalyseRec:
    def _make_mock_abf(self, n_sweeps=3, sampling_rate=20000, duration=1.0):
        """Create a mock ABF object with synthetic spike data."""
        n_samples = int(duration * sampling_rate)
        x_time = np.arange(n_samples) / sampling_rate
        trace = np.full(n_samples, -70.0)
        # Add some spikes
        for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
            if int(t * sampling_rate) < n_samples:
                trace[int(t * sampling_rate)] = 20.0

        mock_abf = MagicMock()
        mock_abf.sweepX = x_time
        mock_abf.sweepY = trace
        mock_abf.dataRate = sampling_rate
        mock_abf.sweepList = list(range(n_sweeps))
        mock_abf.setSweep = MagicMock()
        return mock_abf

    @patch("pynamicgain.observer.os.path.isfile", return_value=True)
    @patch("pynamicgain.observer.PdfPages")
    @patch("pynamicgain.observer.ABF")
    def test_analyses_all_sweeps(
        self, mock_abf_cls, mock_pdf, mock_isfile, sample_setup_config,
    ):
        mock_abf_cls.return_value = self._make_mock_abf(
            n_sweeps=sample_setup_config.n_sweeps,
        )
        mock_pdf.return_value.__enter__ = MagicMock()
        mock_pdf.return_value.__exit__ = MagicMock(return_value=False)

        obs = PyDGAnalysis(sample_setup_config)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            remaining = obs.analyse_rec("/fake/path.abf")
        assert remaining == 0

    def test_file_not_found(self, sample_setup_config):
        obs = PyDGAnalysis(sample_setup_config)
        with pytest.raises(FileNotFoundError, match="ABF file not found"):
            obs.analyse_rec("/nonexistent/file.abf")

    @patch("pynamicgain.observer.os.path.isfile", return_value=True)
    @patch("pynamicgain.observer.PdfPages")
    @patch("pynamicgain.observer.ABF")
    def test_sampling_rate_mismatch(
        self, mock_abf_cls, mock_pdf, mock_isfile, sample_setup_config,
    ):
        mock_abf_cls.return_value = self._make_mock_abf(sampling_rate=10000)
        mock_pdf.return_value.__enter__ = MagicMock()
        mock_pdf.return_value.__exit__ = MagicMock(return_value=False)

        obs = PyDGAnalysis(sample_setup_config)
        with pytest.raises(ValueError, match="Sampling rate mismatch"):
            obs.analyse_rec("/fake/path.abf")
