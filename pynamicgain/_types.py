"""Typed data containers for the PynamicGain package.

Provides frozen dataclasses that replace the previous ``**kwargs`` threading
pattern, giving every function a well-defined, inspectable parameter
contract.
"""


# PynamicGain: Creating Dynamic Gain inputs for Python-based patch clamp setups.
# Copyright (C) 2024–2026  Friedrich Schwarz <friedrich.schwarz@uni.goettingen.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclasses.dataclass(frozen=True)
class SetupConfig:
    """Immutable setup configuration loaded from TOML + CLI overrides.

    All fields are populated by :func:`~pynamicgain.config.load_config`
    which merges the TOML file with CLI arguments and resolves defaults.

    Attributes:
        version: Package version string from the config file.
        master_seed: Master seed for the PCG64DXSM RNG.
        n_seeds_per_setup: Number of seeds allocated per setup id.
        current_seed_index: Current position in the seed sequence.
        setup_id: Unique integer identifying this setup (1-20).
        setup_info: Short description of the setup.
        config_file_creator: Name of the person who created the config.
        creation_time: Timestamp when the config was created.
        stimulus_type: Type of stimulus to generate (currently ``'OU'``).
        n_sweeps: Number of sweeps per input file.
        sampling_rate: Sampling rate of the recordings in Hz.
        duration: Duration of one sweep in seconds.
        out_dir: Directory for generated ABF files.
        input_dir: Directory for patch clamp recordings.
        backup_dir: Directory for backup copies of ABF files.
        analysis_dir: Directory for analysis results.
        setup_dir: Path to the directory containing the TOML file.
        setup_file: Path to the TOML file itself.
        seed_csv: Path to the seed list CSV file.
        settings: The ``[settings]`` TOML section as a dict.
        stimulus: The ``[stimulus]`` TOML section as a dict.
        analysis: The ``[analysis]`` TOML section as a dict.
        std: Standard deviation of the stimulus (from CLI).
        corr_t: Correlation time of the stimulus in ms (from CLI).
    """

    version: str
    master_seed: int
    n_seeds_per_setup: int
    current_seed_index: int
    setup_id: int
    setup_info: str
    config_file_creator: str
    creation_time: str
    stimulus_type: str
    n_sweeps: int
    sampling_rate: int
    duration: float
    out_dir: str
    input_dir: str
    backup_dir: str
    analysis_dir: str
    setup_dir: str
    setup_file: str
    seed_csv: str
    settings: dict[str, Any]
    stimulus: dict[str, Any]
    analysis: dict[str, Any]
    std: float = 0.0
    corr_t: float = 0.0


@dataclasses.dataclass(frozen=True)
class StimulusParams:
    """Parameters for a single stimulus generation call.

    Attributes:
        duration: Duration of the simulation in seconds.
        dt: Time step of the simulation in seconds (``1 / sampling_rate``).
        mu: Mean of the OU process in pA.
        fluctuation_size: Standard deviation (sigma) of the OU process.
        input_correlation: Correlation time (tau) of the input in seconds.
        key: Seed for the random number generator for this sweep.
    """

    duration: float
    dt: float
    mu: float
    fluctuation_size: float
    input_correlation: float
    key: int


@dataclasses.dataclass(frozen=True)
class AnalysisParams:
    """Parameters for spike-train analysis (computation only).

    Attributes:
        refractory_period: Refractory period for LvR calculation in seconds.
        min_spike_height: Minimum spike height for peak detection in mV.
        min_spike_distance: Minimum distance between spikes in samples.
        sampling_rate: Sampling rate in Hz.
    """

    refractory_period: float
    min_spike_height: float
    min_spike_distance: int
    sampling_rate: int


@dataclasses.dataclass(frozen=True)
class VisualisationParams:
    """Parameters for analysis figure generation.

    Attributes:
        trace_start: Start time for the overview trace in seconds.
        trace_duration: Duration of the overview trace in seconds.
        isi_bin_max: Maximum right bin edge for the ISI histogram in seconds.
        isi_bin_width: Width of ISI histogram bins in seconds.
        interval_before_peak: Time before peak for spike snippets in seconds.
        interval_after_peak: Time after peak for spike snippets in seconds.
        snippet_ylim: Y-axis limits ``(min, max)`` for the snippet plot in mV.
    """

    trace_start: float
    trace_duration: float
    isi_bin_max: float
    isi_bin_width: float
    interval_before_peak: float
    interval_after_peak: float
    snippet_ylim: tuple[float, float]


@dataclasses.dataclass
class SpikeMetrics:
    """Results of a spike-train analysis for one sweep.

    Attributes:
        sweep_number: Index of the sweep that was analysed.
        n_spikes: Number of detected spikes.
        mfr: Mean firing rate in Hz.
        cv: Coefficient of variation of the ISI distribution.
        lvR: Local variation ratio of the ISI distribution.
        isi: Inter-spike interval array in seconds.
        peak_indices: Indices of detected spikes in the sweep trace.
        peak_times: Times of detected spikes in seconds.
    """

    sweep_number: int
    n_spikes: int
    mfr: float
    cv: float
    lvR: float
    isi: NDArray[np.float64]
    peak_indices: NDArray[np.intp]
    peak_times: NDArray[np.float64]
