"""Shared fixtures for the PynamicGain test suite."""

import csv
import os

import matplotlib
import numpy as np
import pytest
import tomli_w

matplotlib.use("Agg")  # non-interactive backend for all tests

from pynamicgain._types import (
    AnalysisParams,
    SetupConfig,
    SpikeMetrics,
    VisualisationParams,
)


# -- Minimal valid TOML content for a setup file ----------------------------

SAMPLE_TOML_DICT = {
    "version": "0.1.0",
    "master_seed": 121912940104681416,
    "n_seeds_per_setup": 1_000_000,
    "current_seed_index": 0,
    "setup_id": 1,
    "setup_info": "Test setup",
    "config_file_creator": "pytest",
    "creation_time": "2025-01-01T00:00:00",
    "stimulus_type": "OU",
    "n_sweeps": 3,
    "sampling_rate": 20000,
    "duration": 10.0,
    "out_dir": "",
    "input_dir": "",
    "backup_dir": "",
    "analysis_dir": "",
    "analysis": {
        "type": ["mini_sta"],
        "refractory_period": 0.001,
        "min_spike_height": -5,
        "fraction_min_spike_distance": 0.8,
        "visualise_results": True,
        "visualisation": {
            "trace_start": 0,
            "trace_duration": 20,
            "isi_bin_max": 1,
            "isi_bin_width": 0.25,
            "interval_before_peak": 0.0015,
            "interval_after_peak": 0.0035,
            "snippet_ylim": [-50, 30],
        },
    },
    "settings": {
        "wait_time": 30,
        "update_interval": 5,
        "observation_buffer": 180,
        "input_units": "pA",
    },
    "stimulus": {"OU": {"mu": 0.0}},
}

CSV_HEADER = ["seed index", "seed", "sweep", "file", "backup"]


@pytest.fixture
def sample_setup_config(tmp_path):
    """Return a fully populated SetupConfig with paths in tmp_path."""
    setup_dir = tmp_path / "setup"
    setup_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    seed_csv = setup_dir / "seed_list_setup_1.csv"
    with open(seed_csv, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=CSV_HEADER).writeheader()

    setup_file = setup_dir / "setup_1.toml"
    toml_dict = dict(SAMPLE_TOML_DICT)
    toml_dict["out_dir"] = str(out_dir)
    toml_dict["input_dir"] = str(input_dir)
    toml_dict["backup_dir"] = str(backup_dir)
    toml_dict["analysis_dir"] = str(analysis_dir)
    with open(setup_file, "wb") as f:
        f.write(tomli_w.dumps(toml_dict).encode())

    return SetupConfig(
        version="0.1.0",
        master_seed=121912940104681416,
        n_seeds_per_setup=1_000_000,
        current_seed_index=0,
        setup_id=1,
        setup_info="Test setup",
        config_file_creator="pytest",
        creation_time="2025-01-01T00:00:00",
        stimulus_type="OU",
        n_sweeps=3,
        sampling_rate=20000,
        duration=10.0,
        out_dir=str(out_dir),
        input_dir=str(input_dir),
        backup_dir=str(backup_dir),
        analysis_dir=str(analysis_dir),
        setup_dir=str(setup_dir),
        setup_file=str(setup_file),
        seed_csv=str(seed_csv),
        settings={
            "wait_time": 30,
            "update_interval": 5,
            "observation_buffer": 180,
            "input_units": "pA",
        },
        stimulus={"OU": {"mu": 0.0}},
        analysis={
            "type": ["mini_sta"],
            "refractory_period": 0.001,
            "min_spike_height": -5,
            "fraction_min_spike_distance": 0.8,
            "visualise_results": True,
            "visualisation": {
                "trace_start": 0,
                "trace_duration": 20,
                "isi_bin_max": 1,
                "isi_bin_width": 0.25,
                "interval_before_peak": 0.0015,
                "interval_after_peak": 0.0035,
                "snippet_ylim": [-50, 30],
            },
        },
        std=100.0,
        corr_t=5.0,
    )


@pytest.fixture
def sample_toml_dir(tmp_path):
    """Create a tmp directory with a valid setup_1.toml and seed CSV."""
    setup_dir = tmp_path / "setup"
    setup_dir.mkdir()

    toml_dict = dict(SAMPLE_TOML_DICT)
    toml_dict["out_dir"] = str(tmp_path / "out")
    toml_dict["input_dir"] = str(tmp_path / "input")

    setup_file = setup_dir / "setup_1.toml"
    with open(setup_file, "wb") as f:
        f.write(tomli_w.dumps(toml_dict).encode())

    seed_csv = setup_dir / "seed_list_setup_1.csv"
    with open(seed_csv, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=CSV_HEADER).writeheader()

    return setup_dir


@pytest.fixture
def sample_analysis_params():
    """Return standard AnalysisParams."""
    return AnalysisParams(
        refractory_period=0.001,
        min_spike_height=-5,
        min_spike_distance=16,
        sampling_rate=20000,
    )


@pytest.fixture
def sample_vis_params():
    """Return standard VisualisationParams."""
    return VisualisationParams(
        trace_start=0,
        trace_duration=20,
        isi_bin_max=1,
        isi_bin_width=0.25,
        interval_before_peak=0.0015,
        interval_after_peak=0.0035,
        snippet_ylim=(-50.0, 30.0),
    )


@pytest.fixture
def synthetic_spike_train():
    """Return (x_time, sweep_trace) with 5 spikes at known positions.

    The trace is 1 second long at 20 kHz sampling.  Baseline is -70 mV
    with sharp peaks to +20 mV at t = 0.1, 0.3, 0.5, 0.7, 0.9 s.
    """
    sr = 20000
    duration = 1.0
    n_samples = int(duration * sr)
    x_time = np.arange(n_samples) / sr
    trace = np.full(n_samples, -70.0)

    spike_times = [0.1, 0.3, 0.5, 0.7, 0.9]
    for t in spike_times:
        idx = int(t * sr)
        trace[idx] = 20.0

    return x_time, trace, spike_times
