"""Analysis observation orchestration for the PynamicGain package.

Contains :class:`PyDGAnalysis`, which handles both single-file analysis
and continuous directory observation for newly recorded ABF files.

.. versionchanged:: 0.1.0
   ``PyDGAnalysis`` no longer inherits from ``PyDGBase``. It uses
   composition with :class:`~pynamicgain._types.SetupConfig` and the
   new :func:`~pynamicgain.analysis.compute_spike_metrics` /
   :func:`~pynamicgain.analysis.plot_sweep_analysis` API.
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


import dataclasses
import logging
import os
import time
from datetime import datetime as dt
from datetime import timedelta
from typing import Optional, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from pyabf import ABF

from pynamicgain._types import SetupConfig
from pynamicgain.config import load_config
from pynamicgain.analysis import (
    build_analysis_params,
    build_visualisation_params,
    compute_spike_metrics,
    plot_sweep_analysis,
    get_analysis_function,
    set_analysis_parameters,
)

logger = logging.getLogger(__name__)


class PyDGAnalysis:
    """Analysis class for the dynamic gain calculations.

    .. versionchanged:: 0.1.0
       Uses composition instead of inheriting from ``PyDGBase``.
       Accepts either a :class:`SetupConfig` or a legacy ``cli_args``
       dict for backwards compatibility.

    Attributes:
        config: The frozen setup configuration.
        sweeps2analyse: Sweep indices that still need to be analysed.
    """

    def __init__(
        self,
        cli_args_or_config: Union[dict, SetupConfig],
        start_time: Optional[dt] = None,
    ) -> None:
        """Initialise from a config or legacy CLI args dict.

        Args:
            cli_args_or_config: Either a :class:`SetupConfig` instance
                (preferred) or a dict of CLI arguments (legacy path).
            start_time: If provided, enables observation mode with a
                time-limited directory watch. Defaults to None.
        """
        if isinstance(cli_args_or_config, SetupConfig):
            self.config = cli_args_or_config
        else:
            self.config = load_config(cli_args_or_config)

        cfg = self.config

        # Build typed analysis parameters
        self._analysis_params = build_analysis_params(
            cfg.analysis, cfg.sampling_rate,
        )
        self._visualise = cfg.analysis.get('visualise_results', True)
        if 'visualisation' in cfg.analysis:
            self._vis_params = build_visualisation_params(cfg.analysis['visualisation'])
        else:
            self._vis_params = None

        # Observation mode setup
        if start_time:
            self._start_time = start_time
            observation_buffer = cfg.settings.get('observation_buffer', 180)
            self._observation_duration = cfg.n_sweeps * cfg.duration + observation_buffer
            self._max_time = start_time + timedelta(seconds=self._observation_duration)
        else:
            self._start_time = self._max_time = None

        self.sweeps2analyse = list(np.arange(cfg.n_sweeps, dtype=int))
        self._fig_list: list[plt.Figure] = []

        # Backwards compatibility: expose config fields as instance attrs
        for field in dataclasses.fields(cfg):
            if not hasattr(self, field.name):
                setattr(self, field.name, getattr(cfg, field.name))

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        attrs = '\n\t'.join(
            f"{f.name + ': ': <25}{getattr(self.config, f.name)!r}"
            for f in dataclasses.fields(self.config)
        )
        return f'\n{self.__class__.__name__}:\n\t{attrs}'

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return self.__repr__()

    def observe(self) -> int:
        """Observe a directory and analyse newly generated ABF files.

        Polls ``input_dir`` at regular intervals until all sweeps have
        been analysed or the time limit is reached.

        Returns:
            The number of sweeps that remain unanalysed.
        """
        cfg = self.config
        logger.info("Start observing '%s' for new files to analyse...", cfg.input_dir)

        while dt.now() < self._max_time:
            time.sleep(cfg.settings['update_interval'])

            files = os.listdir(cfg.input_dir)
            files = [f for f in files if f.endswith('.abf')]

            if len(files) == 0:
                continue

            last_modified = [
                os.path.getmtime(os.path.join(cfg.input_dir, f)) for f in files
            ]
            latest_mod_time = dt.fromtimestamp(np.max(last_modified))

            if latest_mod_time < self._start_time + timedelta(seconds=cfg.settings['wait_time']):
                continue

            latest_file = files[np.argmax(last_modified)]
            self.analyse_rec(os.path.join(cfg.input_dir, latest_file))

            if len(self.sweeps2analyse) == 0:
                plt.close('all')
                break

        if len(self.sweeps2analyse) > 0:
            logger.warning("Not all sweeps analysed. Remaining sweeps: %s", self.sweeps2analyse)

        return len(self.sweeps2analyse)

    def analyse_rec(self, file2analyse: str) -> int:
        """Analyse all available sweeps in a single ABF file.

        Can be called explicitly to analyse existing data or by the
        observer to analyse newly recorded data.

        Args:
            file2analyse: Absolute path to the ABF file to analyse.

        Returns:
            The number of sweeps that remain unanalysed.

        Raises:
            FileNotFoundError: If the ABF file does not exist.
            ValueError: If the sampling rate of the recording does not
                match the setup configuration.

        Note:
            ABF sweeps cannot be read concurrently. The current sweep is
            selected via ``abf.setSweep`` and its data accessed through
            ``abf.sweepY``. The full sweep list is in ``abf.sweepList``.
        """
        cfg = self.config

        if not os.path.isfile(file2analyse):
            raise FileNotFoundError(
                f"ABF file not found: '{file2analyse}'. "
                f"Please check the file path."
            )

        only_filename = os.path.splitext(os.path.basename(file2analyse))[0]
        if len(self.sweeps2analyse) == cfg.n_sweeps:
            logger.info("Starting analysis of '%s'...", only_filename)
            self._fig_list = []

        abf_file = ABF(file2analyse)

        # read (meta) data
        x_time = abf_file.sweepX
        sampling_rate = abf_file.dataRate

        if sampling_rate != cfg.sampling_rate:
            raise ValueError(
                f"Sampling rate mismatch in '{file2analyse}': "
                f"expected {cfg.sampling_rate} Hz, got {sampling_rate} Hz. "
                f"Please check the recording settings."
            )

        for c_sweep in abf_file.sweepList:
            if c_sweep not in self.sweeps2analyse:
                continue
            else:
                self.sweeps2analyse.remove(c_sweep)

            abf_file.setSweep(c_sweep)
            sweep_trace = abf_file.sweepY

            # Use the new split API
            metrics = compute_spike_metrics(
                x_time, sweep_trace, self._analysis_params, c_sweep,
            )

            if metrics is not None and self._visualise and self._vis_params is not None:
                fig = plot_sweep_analysis(
                    x_time, sweep_trace, metrics,
                    self._analysis_params, self._vis_params,
                )
                self._fig_list.append(fig)
            elif metrics is not None and self._visualise:
                # Fallback: no vis params available, skip plot
                logger.warning(
                    "Visualisation requested but no visualisation params available. "
                    "Skipping plot for sweep %d.", c_sweep,
                )

            with PdfPages(os.path.join(cfg.analysis_dir, f'{only_filename}.pdf')) as pdf:
                for fig in self._fig_list:
                    pdf.savefig(fig)

        return len(self.sweeps2analyse)
