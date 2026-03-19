"""Module for on-the-fly analysis of newly generated data.

Currently this is a super simple peak finding and subsequent spike train analysis.
However, this can be extended to more complex analysis in the future.
"""


# PynamicGain: Creating Dynamic Gain inputs for Python-based patch clamp setups.
# Copyright (C) 2024  Friedrich Schwarz <friedrichschwarz@unigoettingen.de>

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


import warnings

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks


def get_analysis_function(what: str = 'mini_sta'):
    """Return the analysis function based on the input."""
    if what == 'mini_sta':
        return minimal_spike_train_analysis
    else:
        raise ValueError(f"Unknown analysis type: {what}")


def set_analysis_parameters(what: str = 'mini_sta', **kwargs):
    """Creates/Parses the relevant parameters for the analysis."""
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
    ) -> plt.figure:
    """Minimal Spike Train Analysis of Patch Clamp Data.
    
    This function takes a numpy voltage trace as input.
    This function does not handle any I/O operations.
    
    CV and LvR adapted from: 
        https://gist.github.com/fschwar4/8e9044273716cfea5a76653daeb0d170

    Args:
        x_time (np.ndarray): time array
        sweep_trace (np.ndarray): voltage trace
        refractory_period (float, optional): refractory period for LvR calculation. Defaults to 0.001.
        min_spike_height (float, optional): minimum spike height for peak detection in mV. Defaults to -5.
        min_spike_distance (int, optional): minimum spike distance for peak detection in samples. Defaults to 10.
        sampling_rate (int, optional): sampling rate in Hz. Defaults to 50_000.
        visualise (bool, optional): whether to visualise the results. Defaults to False.
        sweep_number (int, optional): sweep number. Defaults to 0.
        out_file_path (str, optional): file path for saving the figure. Defaults to '.'.
        
    Returns:
        tuple: mean firing rate, coefficient of variation, local variation ratio
    """
    # find peaks with most basic algorithm; TODO: can be improved in the future
    peaks_ = find_peaks(sweep_trace, height=min_spike_height, distance=min_spike_distance)[0]
    peak_times = x_time[peaks_]
    n_spikes = len(peak_times)

    # calculate mean firing rate
    mfr = n_spikes / x_time[-1]

    if n_spikes < 2:
        isi = np.array([])
        cv = np.nan
        lvR = np.nan
        if n_spikes == 0:
            warnings.warn(f"Sweep {sweep_number}: No spikes detected.")
        else:
            warnings.warn(f"Sweep {sweep_number}: Only 1 spike detected. CV and LvR cannot be computed.")
    elif n_spikes == 2:
        isi = np.diff(peak_times)
        cv = np.std(isi) / np.mean(isi)
        lvR = np.nan
        warnings.warn(f"Sweep {sweep_number}: Only 2 spikes detected. LvR cannot be computed.")
    else:
        isi = np.diff(peak_times)
        cv = np.std(isi) / np.mean(isi)
        # LvR calculation
        s_ = 3 / (len(isi) - 1)
        si_ = isi[:-1] + isi[1:]
        ft_ = 1 - ((4 * (isi[:-1] * isi[1:])) / si_**2)
        st_ = 1 + ((4 * refractory_period) / si_)
        lvR = s_ * np.sum(ft_ * st_)
    
    if visualise == True:
        _bp = int(kwargs['interval_before_peak'] * sampling_rate)  # data points before peak
        _ap = int(kwargs['interval_after_peak'] * sampling_rate)  # data points after peak 
        _snippet_length = _bp + _ap + 1  # +1 for the peak itself
        
        fig, axs = plt.subplots(3, 1, figsize = (15, 10), tight_layout = True)
        
        axs[0].axhline(0, color = 'grey', linestyle = '--', lw = 0.5, alpha = 0.8)
        axs[0].plot(x_time, sweep_trace)
        axs[0].scatter(peak_times, sweep_trace[peaks_], color = 'red', marker = 'x')
        axs[0].set_title('Sweep Trace with Detected Peaks')
        axs[0].set_xlabel('Time (s)')
        axs[0].set_ylabel('Voltage (mV)')
        
        _x_end = kwargs['trace_start'] + kwargs['trace_duration']
        axs[0].set_xlim(
            kwargs['trace_start']-0.1,
            _x_end+0.1 if _x_end < x_time[-1] else x_time[-1]+0.1
        )

        bin_max = kwargs['isi_bin_max']
        bin_width = kwargs['isi_bin_width']
        axs[1].hist(isi, range=(0, bin_max), bins=int(np.ceil(bin_max/bin_width)))
        axs[1].set_title('ISI Histogram')
        axs[1].set_xlabel('ISI (s)')
        axs[1].set_ylabel('Count')

        snip_idx = []
        if len(peaks_) > 0:
            for tp in peaks_:
                _idx = np.arange(
                    max([0, tp-_bp-1]),  # not before the start
                    min([len(sweep_trace), tp+_ap]),  # not after the end
                    dtype=np.int32).ravel()
                if len(_idx) != _snippet_length:  # skip spikes at the borders
                    continue
                snip_idx.append(_idx)

        if len(snip_idx) > 0:
            snip_idx = np.concatenate(snip_idx)
            snippets = sweep_trace[snip_idx].reshape(-1, _snippet_length)
            _xtime = np.arange(_snippet_length) / sampling_rate * 1e3
            axs[2].plot(_xtime, snippets.T, color='black', alpha=0.1, linewidth=0.75)

        axs[2].text(0.85, 0.85, f'MFR: {mfr:.2f} Hz\nCV: {cv:.2f}\nLvR: {lvR:.2f}')
        axs[2].set_title('Spike Snippets')
        axs[2].set_xlabel('Time (ms)')
        axs[2].set_ylabel('Voltage (mV)')
        axs[2].set_ylim(*kwargs['snippet_ylim'])
        
        fig.suptitle(f'Sweep {sweep_number}')
        
    else:
        fig = None
        
    print(
            f'Sweep {sweep_number} has the following properties:\n'
            f'\tMFR: {mfr:.2f} Hz\n'
            f'\tCV: {cv:.2f}\n'
            f'\tLVR: {lvR:.2f}\n'
        )
        
    return fig
