"""Tests for pynamicgain._types dataclass contracts."""

import dataclasses

import numpy as np
import pytest

from pynamicgain._types import (
    AnalysisParams,
    SetupConfig,
    SpikeMetrics,
    StimulusParams,
    VisualisationParams,
)


class TestSetupConfig:
    def test_frozen(self, sample_setup_config):
        with pytest.raises(dataclasses.FrozenInstanceError):
            sample_setup_config.version = "9.9.9"

    def test_defaults(self):
        """std and corr_t default to 0.0 when not provided."""
        cfg = SetupConfig(
            version="0.1.0",
            master_seed=0,
            n_seeds_per_setup=1,
            current_seed_index=0,
            setup_id=1,
            setup_info="",
            config_file_creator="",
            creation_time="",
            stimulus_type="OU",
            n_sweeps=1,
            sampling_rate=20000,
            duration=1.0,
            out_dir="",
            input_dir="",
            backup_dir="",
            analysis_dir="",
            setup_dir="",
            setup_file="",
            seed_csv="",
            settings={},
            stimulus={},
            analysis={},
        )
        assert cfg.std == 0.0
        assert cfg.corr_t == 0.0

    def test_asdict_roundtrip(self, sample_setup_config):
        d = dataclasses.asdict(sample_setup_config)
        cfg2 = SetupConfig(**d)
        assert cfg2 == sample_setup_config


class TestStimulusParams:
    def test_frozen(self):
        p = StimulusParams(
            duration=10.0, dt=0.00005, mu=0.0,
            fluctuation_size=100.0, input_correlation=5.0, key=42,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.duration = 99.0

    def test_fields(self):
        p = StimulusParams(
            duration=10.0, dt=0.00005, mu=0.0,
            fluctuation_size=100.0, input_correlation=5.0, key=42,
        )
        assert p.duration == 10.0
        assert p.key == 42


class TestAnalysisParams:
    def test_frozen(self):
        p = AnalysisParams(
            refractory_period=0.001, min_spike_height=-5,
            min_spike_distance=16, sampling_rate=20000,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.sampling_rate = 10000


class TestVisualisationParams:
    def test_frozen(self):
        p = VisualisationParams(
            trace_start=0, trace_duration=20,
            isi_bin_max=1, isi_bin_width=0.25,
            interval_before_peak=0.0015, interval_after_peak=0.0035,
            snippet_ylim=(-50, 30),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.trace_start = 99


class TestSpikeMetrics:
    def test_mutable(self):
        m = SpikeMetrics(
            sweep_number=0, n_spikes=5, mfr=10.0,
            cv=0.5, lvR=0.3,
            isi=np.array([0.1, 0.1]),
            peak_indices=np.array([100, 200]),
            peak_times=np.array([0.005, 0.01]),
        )
        m.n_spikes = 10
        assert m.n_spikes == 10

    def test_not_frozen(self):
        """SpikeMetrics is explicitly NOT frozen."""
        assert not dataclasses.fields(SpikeMetrics)[0].metadata.get("frozen", False)
        # Simpler check: it has no __delattr__ override from frozen
        m = SpikeMetrics(
            sweep_number=0, n_spikes=0, mfr=0.0,
            cv=0.0, lvR=0.0,
            isi=np.array([]),
            peak_indices=np.array([], dtype=np.intp),
            peak_times=np.array([]),
        )
        m.mfr = 42.0
        assert m.mfr == 42.0
