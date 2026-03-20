"""Tests for pynamicgain.analysis."""

import warnings

import matplotlib
import numpy as np
import pytest

from pynamicgain._types import AnalysisParams, SpikeMetrics, VisualisationParams
from pynamicgain.analysis import (
    build_analysis_params,
    build_visualisation_params,
    compute_spike_metrics,
    get_analysis_function,
    minimal_spike_train_analysis,
    plot_sweep_analysis,
    set_analysis_parameters,
)


# -- compute_spike_metrics --------------------------------------------------

class TestComputeSpikeMetrics:
    def test_known_spikes(self, synthetic_spike_train, sample_analysis_params):
        x_time, trace, spike_times = synthetic_spike_train
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            metrics = compute_spike_metrics(x_time, trace, sample_analysis_params, 0)

        assert metrics is not None
        assert metrics.n_spikes == 5
        assert metrics.sweep_number == 0
        np.testing.assert_allclose(metrics.peak_times, spike_times, atol=1e-4)

    def test_mfr(self, synthetic_spike_train, sample_analysis_params):
        x_time, trace, _ = synthetic_spike_train
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            metrics = compute_spike_metrics(x_time, trace, sample_analysis_params, 0)
        # 5 spikes in ~1 second
        assert abs(metrics.mfr - 5.0) < 0.1

    def test_zero_spikes(self, sample_analysis_params):
        x_time = np.arange(20000) / 20000
        trace = np.full(20000, -70.0)  # flat, no spikes
        with pytest.warns(UserWarning, match="No spikes"):
            metrics = compute_spike_metrics(x_time, trace, sample_analysis_params, 0)
        assert metrics.n_spikes == 0
        assert np.isnan(metrics.cv)
        assert np.isnan(metrics.lvR)

    def test_one_spike(self, sample_analysis_params):
        x_time = np.arange(20000) / 20000
        trace = np.full(20000, -70.0)
        trace[10000] = 20.0  # single spike
        with pytest.warns(UserWarning, match="Only 1 spike"):
            metrics = compute_spike_metrics(x_time, trace, sample_analysis_params, 0)
        assert metrics.n_spikes == 1
        assert np.isnan(metrics.cv)

    def test_two_spikes(self, sample_analysis_params):
        x_time = np.arange(20000) / 20000
        trace = np.full(20000, -70.0)
        trace[4000] = 20.0
        trace[16000] = 20.0
        with pytest.warns(UserWarning, match="Only 2 spikes"):
            metrics = compute_spike_metrics(x_time, trace, sample_analysis_params, 0)
        assert metrics.n_spikes == 2
        assert not np.isnan(metrics.cv)  # CV can be computed with 2
        assert np.isnan(metrics.lvR)     # LvR needs 3+

    def test_empty_trace(self, sample_analysis_params):
        with pytest.warns(UserWarning, match="Empty recording"):
            result = compute_spike_metrics(
                np.array([]), np.array([]),
                sample_analysis_params, 0,
            )
        assert result is None

    def test_regular_isi_cv_zero(self, sample_analysis_params):
        """Perfectly regular spikes should have CV ≈ 0."""
        sr = 20000
        x_time = np.arange(sr * 2) / sr  # 2 seconds
        trace = np.full(sr * 2, -70.0)
        # Spikes every 0.1s: at 0.1, 0.2, ..., 1.9
        for t in np.arange(0.1, 2.0, 0.1):
            trace[int(t * sr)] = 20.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            metrics = compute_spike_metrics(x_time, trace, sample_analysis_params, 0)
        assert metrics.cv < 0.01

    def test_regular_isi_lvr_near_zero(self, sample_analysis_params):
        """Perfectly regular spikes should have LvR ≈ 0."""
        sr = 20000
        x_time = np.arange(sr * 2) / sr
        trace = np.full(sr * 2, -70.0)
        for t in np.arange(0.1, 2.0, 0.1):
            trace[int(t * sr)] = 20.0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            metrics = compute_spike_metrics(x_time, trace, sample_analysis_params, 0)
        assert abs(metrics.lvR) < 0.05


# -- plot_sweep_analysis ----------------------------------------------------

class TestPlotSweepAnalysis:
    def test_returns_figure(
        self, synthetic_spike_train, sample_analysis_params, sample_vis_params,
    ):
        x_time, trace, _ = synthetic_spike_train
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            metrics = compute_spike_metrics(x_time, trace, sample_analysis_params, 0)

        fig = plot_sweep_analysis(
            x_time, trace, metrics, sample_analysis_params, sample_vis_params,
        )
        assert fig is not None
        assert len(fig.axes) == 3
        matplotlib.pyplot.close(fig)


# -- build_analysis_params / build_visualisation_params ---------------------

class TestBuildAnalysisParams:
    def test_correct_fields(self):
        cfg = {
            "refractory_period": 0.001,
            "min_spike_height": -5,
            "fraction_min_spike_distance": 0.8,
        }
        params = build_analysis_params(cfg, sampling_rate=20000)
        assert params.refractory_period == 0.001
        assert params.min_spike_height == -5
        assert params.min_spike_distance == int(0.8 * 0.001 * 20000)
        assert params.sampling_rate == 20000


class TestBuildVisualisationParams:
    def test_correct_fields(self):
        cfg = {
            "trace_start": 0,
            "trace_duration": 20,
            "isi_bin_max": 1,
            "isi_bin_width": 0.25,
            "interval_before_peak": 0.0015,
            "interval_after_peak": 0.0035,
            "snippet_ylim": [-50, 30],
        }
        params = build_visualisation_params(cfg)
        assert params.trace_duration == 20
        assert params.snippet_ylim == (-50, 30)


# -- get_analysis_function / set_analysis_parameters ------------------------

class TestGetAnalysisFunction:
    def test_mini_sta(self):
        func = get_analysis_function("mini_sta")
        assert func is minimal_spike_train_analysis

    def test_unknown(self):
        with pytest.raises(ValueError, match="Unknown analysis type"):
            get_analysis_function("nonexistent")


class TestSetAnalysisParameters:
    def test_mini_sta(self):
        params = set_analysis_parameters(
            "mini_sta",
            analysis={
                "refractory_period": 0.001,
                "min_spike_height": -5,
                "fraction_min_spike_distance": 0.8,
                "visualise_results": True,
            },
            sampling_rate=20000,
        )
        assert "refractory_period" in params
        assert "min_spike_distance" in params

    def test_unknown(self):
        with pytest.raises(ValueError, match="Unknown analysis type"):
            set_analysis_parameters("nonexistent", analysis={}, sampling_rate=20000)
