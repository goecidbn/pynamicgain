"""Module for on-the-fly analysis of newly generated data.

Currently this is a super simple peak finding and subsequent spike train analysis.
However, this can be extended to more complex analysis in the future.

.. versionchanged:: 0.1.0
   Analysis split into :func:`compute_spike_metrics` (pure computation) and
   :func:`plot_sweep_analysis` (visualisation). The legacy
   :func:`minimal_spike_train_analysis` wrapper is retained for backwards
   compatibility.
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

import logging
import warnings
from typing import Optional, TYPE_CHECKING

import numpy as np
from scipy.signal import find_peaks

from pynamicgain._types import AnalysisParams, SpikeMetrics, VisualisationParams

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Dispatch helpers (unchanged public API)
# ------------------------------------------------------------------ #

def get_analysis_function(what: str = 'mini_sta'):
    """Return the analysis function matching the given type name.

    Args:
        what: Analysis type identifier. Defaults to ``'mini_sta'``.

    Returns:
        The callable analysis function.

    Raises:
        ValueError: If ``what`` is not a recognised analysis type.
    """
    if what == 'mini_sta':
        return minimal_spike_train_analysis
    else:
        raise ValueError(f"Unknown analysis type: {what}")


def set_analysis_parameters(what: str = 'mini_sta', **kwargs) -> dict:
    """Extract and normalise parameters for the specified analysis type.

    Args:
        what: Analysis type identifier. Defaults to ``'mini_sta'``.
        **kwargs: Must contain ``analysis`` and ``sampling_rate`` keys.

    Returns:
        Dictionary of keyword arguments for the analysis function.

    Raises:
        ValueError: If ``what`` is not a recognised analysis type.
    """
    if what == 'mini_sta':
        time_btw2spikes = kwargs['analysis']['fraction_min_spike_distance']
        time_btw2spikes *= kwargs['analysis']['refractory_period']
        time_btw2spikes = int(time_btw2spikes * kwargs['sampling_rate'])

        return {
            "refractory_period": kwargs['analysis']['refractory_period'],
            "min_spike_height": kwargs['analysis']['min_spike_height'],
            "min_spike_distance": time_btw2spikes,
            "sampling_rate": kwargs['sampling_rate'],
            "visualise": kwargs['analysis']['visualise_results'],
        }
    else:
        raise ValueError(f"Unknown analysis type: {what}")


def build_analysis_params(analysis_cfg: dict, sampling_rate: int) -> AnalysisParams:
    """Build an :class:`AnalysisParams` from a raw analysis config dict.

    Args:
        analysis_cfg: The ``[analysis]`` section of the TOML config.
        sampling_rate: Sampling rate in Hz.

    Returns:
        A frozen :class:`AnalysisParams` instance.
    """
    time_btw2spikes = analysis_cfg['fraction_min_spike_distance']
    time_btw2spikes *= analysis_cfg['refractory_period']
    time_btw2spikes = int(time_btw2spikes * sampling_rate)

    return AnalysisParams(
        refractory_period=analysis_cfg['refractory_period'],
        min_spike_height=analysis_cfg['min_spike_height'],
        min_spike_distance=time_btw2spikes,
        sampling_rate=sampling_rate,
    )


def build_visualisation_params(vis_cfg: dict) -> VisualisationParams:
    """Build a :class:`VisualisationParams` from a raw visualisation config dict.

    Args:
        vis_cfg: The ``[analysis.visualisation]`` section of the TOML config.

    Returns:
        A frozen :class:`VisualisationParams` instance.
    """
    return VisualisationParams(
        trace_start=vis_cfg['trace_start'],
        trace_duration=vis_cfg['trace_duration'],
        isi_bin_max=vis_cfg['isi_bin_max'],
        isi_bin_width=vis_cfg['isi_bin_width'],
        interval_before_peak=vis_cfg['interval_before_peak'],
        interval_after_peak=vis_cfg['interval_after_peak'],
        snippet_ylim=tuple(vis_cfg['snippet_ylim']),
    )


# ------------------------------------------------------------------ #
# New API: pure computation
# ------------------------------------------------------------------ #

def compute_spike_metrics(
    x_time: np.ndarray,
    sweep_trace: np.ndarray,
    params: AnalysisParams,
    sweep_number: int,
) -> Optional[SpikeMetrics]:
    """Detect spikes and compute firing statistics (pure computation).

    Detects spikes via :func:`scipy.signal.find_peaks`, then computes
    mean firing rate (MFR), coefficient of variation (CV) and local
    variation ratio (LvR). Does not perform any I/O or plotting.

    CV and LvR adapted from
    https://gist.github.com/fschwar4/8e9044273716cfea5a76653daeb0d170

    Args:
        x_time: Time array in seconds.
        sweep_trace: Voltage trace in mV.
        params: Analysis parameters.
        sweep_number: Index of the sweep being analysed.

    Returns:
        A :class:`SpikeMetrics` instance, or ``None`` for empty traces.

    Warns:
        UserWarning: When fewer than 3 spikes are detected, as some
            metrics cannot be computed.

    .. versionadded:: 0.1.0
    """
    # Guard against zero-length recordings
    if len(x_time) == 0 or len(sweep_trace) == 0:
        warnings.warn(
            f"Sweep {sweep_number}: Empty recording (zero-length trace). "
            f"Skipping analysis."
        )
        return None

    # find peaks with most basic algorithm
    peaks_ = find_peaks(
        sweep_trace,
        height=params.min_spike_height,
        distance=params.min_spike_distance,
    )[0]
    peak_times = x_time[peaks_]
    n_spikes = len(peak_times)

    # calculate mean firing rate (guard against zero-duration recording)
    recording_duration = x_time[-1]
    if recording_duration > 0:
        mfr = n_spikes / recording_duration
    else:
        mfr = 0.0
        warnings.warn(
            f"Sweep {sweep_number}: Recording duration is zero. MFR set to 0."
        )

    if n_spikes < 2:
        isi = np.array([])
        cv = np.nan
        lvR = np.nan
        if n_spikes == 0:
            warnings.warn(f"Sweep {sweep_number}: No spikes detected.")
        else:
            warnings.warn(
                f"Sweep {sweep_number}: Only 1 spike detected. "
                f"CV and LvR cannot be computed."
            )
    elif n_spikes == 2:
        isi = np.diff(peak_times)
        mean_isi = np.mean(isi)
        cv = np.std(isi) / mean_isi if mean_isi > 0 else np.nan
        lvR = np.nan
        warnings.warn(
            f"Sweep {sweep_number}: Only 2 spikes detected. "
            f"LvR cannot be computed."
        )
    else:
        isi = np.diff(peak_times)
        mean_isi = np.mean(isi)
        cv = np.std(isi) / mean_isi if mean_isi > 0 else np.nan
        # LvR calculation
        s_ = 3 / (len(isi) - 1)
        si_ = isi[:-1] + isi[1:]
        ft_ = 1 - ((4 * (isi[:-1] * isi[1:])) / si_**2)
        st_ = 1 + ((4 * params.refractory_period) / si_)
        lvR = s_ * np.sum(ft_ * st_)

    logger.info(
        "Sweep %d: MFR=%.2f Hz, CV=%.2f, LvR=%.2f",
        sweep_number, mfr, cv, lvR,
    )

    return SpikeMetrics(
        sweep_number=sweep_number,
        n_spikes=n_spikes,
        mfr=mfr,
        cv=cv,
        lvR=lvR,
        isi=isi,
        peak_indices=peaks_,
        peak_times=peak_times,
    )


# ------------------------------------------------------------------ #
# New API: visualisation
# ------------------------------------------------------------------ #

def plot_sweep_analysis(
    x_time: np.ndarray,
    sweep_trace: np.ndarray,
    metrics: SpikeMetrics,
    params: AnalysisParams,
    vis_params: VisualisationParams,
) -> "plt.Figure":
    """Create a 3-panel analysis figure from pre-computed metrics.

    Panels: (1) sweep trace with detected peaks, (2) ISI histogram,
    (3) spike snippets with MFR/CV/LvR annotation.

    Args:
        x_time: Time array in seconds.
        sweep_trace: Voltage trace in mV.
        metrics: Pre-computed spike metrics from :func:`compute_spike_metrics`.
        params: Analysis parameters (for sampling rate).
        vis_params: Visualisation parameters.

    Returns:
        A matplotlib Figure with three subplots.

    .. versionadded:: 0.1.0
    """
    import matplotlib.pyplot as plt  # lazy import for lightweight usage

    _bp = int(vis_params.interval_before_peak * params.sampling_rate)
    _ap = int(vis_params.interval_after_peak * params.sampling_rate)
    _snippet_length = _bp + _ap + 1

    fig, axs = plt.subplots(3, 1, figsize=(15, 10), tight_layout=True)

    # Panel 1: Sweep trace with detected peaks
    axs[0].axhline(0, color='grey', linestyle='--', lw=0.5, alpha=0.8)
    axs[0].plot(x_time, sweep_trace)
    axs[0].scatter(
        metrics.peak_times,
        sweep_trace[metrics.peak_indices],
        color='red', marker='x',
    )
    axs[0].set_title('Sweep Trace with Detected Peaks')
    axs[0].set_xlabel('Time (s)')
    axs[0].set_ylabel('Voltage (mV)')

    _x_end = vis_params.trace_start + vis_params.trace_duration
    axs[0].set_xlim(
        vis_params.trace_start - 0.1,
        _x_end + 0.1 if _x_end < x_time[-1] else x_time[-1] + 0.1,
    )

    # Panel 2: ISI histogram
    axs[1].hist(
        metrics.isi,
        range=(0, vis_params.isi_bin_max),
        bins=int(np.ceil(vis_params.isi_bin_max / vis_params.isi_bin_width)),
    )
    axs[1].set_title('ISI Histogram')
    axs[1].set_xlabel('ISI (s)')
    axs[1].set_ylabel('Count')

    # Panel 3: Spike snippets
    snip_idx = []
    if len(metrics.peak_indices) > 0:
        for tp in metrics.peak_indices:
            _idx = np.arange(
                max([0, tp - _bp - 1]),
                min([len(sweep_trace), tp + _ap]),
                dtype=np.int32,
            ).ravel()
            if len(_idx) != _snippet_length:
                continue
            snip_idx.append(_idx)

    if len(snip_idx) > 0:
        snip_idx = np.concatenate(snip_idx)
        snippets = sweep_trace[snip_idx].reshape(-1, _snippet_length)
        _xtime = np.arange(_snippet_length) / params.sampling_rate * 1e3
        axs[2].plot(_xtime, snippets.T, color='black', alpha=0.1, linewidth=0.75)

    axs[2].text(
        0.85, 0.85,
        f'MFR: {metrics.mfr:.2f} Hz\nCV: {metrics.cv:.2f}\nLvR: {metrics.lvR:.2f}',
    )
    axs[2].set_title('Spike Snippets')
    axs[2].set_xlabel('Time (ms)')
    axs[2].set_ylabel('Voltage (mV)')
    axs[2].set_ylim(*vis_params.snippet_ylim)

    fig.suptitle(f'Sweep {metrics.sweep_number}')

    return fig


# ------------------------------------------------------------------ #
# Legacy API (backwards-compatible wrapper)
# ------------------------------------------------------------------ #

def minimal_spike_train_analysis(
    x_time: np.ndarray,
    sweep_trace: np.ndarray,
    refractory_period: float,
    min_spike_height: float,
    min_spike_distance: int,
    sampling_rate: int,
    sweep_number: int,
    visualise: bool = False,
    **kwargs
) -> Optional["plt.Figure"]:
    """Perform a minimal spike train analysis on patch clamp data.

    .. deprecated:: 0.1.0
       Use :func:`compute_spike_metrics` and :func:`plot_sweep_analysis`
       instead. This wrapper is retained for backwards compatibility.

    Detects spikes via :func:`scipy.signal.find_peaks`, then computes
    mean firing rate (MFR), coefficient of variation (CV) and local
    variation ratio (LvR). Does not handle any I/O operations.

    CV and LvR adapted from
    https://gist.github.com/fschwar4/8e9044273716cfea5a76653daeb0d170

    Args:
        x_time: Time array in seconds.
        sweep_trace: Voltage trace in mV.
        refractory_period: Refractory period for the LvR calculation
            in seconds.
        min_spike_height: Minimum spike height for peak detection in mV.
        min_spike_distance: Minimum distance between spikes in samples.
        sampling_rate: Sampling rate in Hz.
        sweep_number: Index of the sweep being analysed.
        visualise: Whether to create a 3-panel figure with trace,
            ISI histogram and spike snippets. Defaults to False.
        **kwargs: Additional visualisation parameters (e.g.
            ``trace_start``, ``trace_duration``, ``isi_bin_max``,
            ``isi_bin_width``, ``interval_before_peak``,
            ``interval_after_peak``, ``snippet_ylim``).

    Returns:
        A matplotlib Figure if ``visualise`` is True, otherwise None.

    Warns:
        UserWarning: When fewer than 3 spikes are detected, as some
            metrics cannot be computed.
    """
    params = AnalysisParams(
        refractory_period=refractory_period,
        min_spike_height=min_spike_height,
        min_spike_distance=min_spike_distance,
        sampling_rate=sampling_rate,
    )

    metrics = compute_spike_metrics(x_time, sweep_trace, params, sweep_number)

    if metrics is None:
        return None

    if visualise:
        vis_params = VisualisationParams(
            trace_start=kwargs.get('trace_start', 0),
            trace_duration=kwargs.get('trace_duration', 20),
            isi_bin_max=kwargs.get('isi_bin_max', 1),
            isi_bin_width=kwargs.get('isi_bin_width', 0.25),
            interval_before_peak=kwargs.get('interval_before_peak', 0.0015),
            interval_after_peak=kwargs.get('interval_after_peak', 0.0035),
            snippet_ylim=tuple(kwargs.get('snippet_ylim', [-50, 30])),
        )
        return plot_sweep_analysis(x_time, sweep_trace, metrics, params, vis_params)

    return None
