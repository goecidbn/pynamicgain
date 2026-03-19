"""Analysis observation orchestration for the PynamicGain package.

Contains :class:`PyDGAnalysis`, which handles both single-file analysis
and continuous directory observation for newly recorded ABF files.
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


import logging
import os
import time
from datetime import datetime as dt
from datetime import timedelta
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from pyabf import ABF

from pynamicgain.base import PyDGBase
from pynamicgain.analysis import get_analysis_function, set_analysis_parameters

logger = logging.getLogger(__name__)


class PyDGAnalysis(PyDGBase):
    """Analysis class for the dynamic gain calculations.

    .. inheritance-diagram:: pynamicgain.observer.PyDGAnalysis
        :parts: 1

    Attributes:
        _start_time: The start time for the observation.
        _max_time: The maximum time for the observation.
        _observation_duration: Estimated duration of recording plus buffer
            in seconds.
        sweeps2analyse: Sweep indices that still need to be analysed.
        input_dir: The directory to watch for new recordings.
        analysis_dir: The directory where analysis results will be stored.
        analysis: The analysis settings (including visualisation settings).
    """

    def __init__(self, cli_args: dict, start_time: Optional[dt] = None) -> None:
        """Initialise from setup configurations and CLI arguments.

        Args:
            cli_args: Dictionary of command line arguments.
            start_time: If provided, enables observation mode with a
                time-limited directory watch. Defaults to None.
        """
        super().__init__(cli_args)

        if start_time:
            self._start_time = start_time
            observation_buffer = self.settings.get('observation_buffer', 180)
            self._observation_duration = self.n_sweeps * self.duration + observation_buffer
            self._max_time = start_time + timedelta(seconds=self._observation_duration)

        else:
            self._start_time = self._max_time = None

        self.sweeps2analyse = list(np.arange(self.n_sweeps, dtype=int))

    def observe(self) -> int:
        """Observe a directory and analyse newly generated ABF files.

        Polls ``input_dir`` at regular intervals until all sweeps have
        been analysed or the time limit is reached.

        Returns:
            The number of sweeps that remain unanalysed.
        """
        logger.info("Start observing '%s' for new files to analyse...", self.input_dir)
        while dt.now() < self._max_time:
            time.sleep(self.settings['update_interval'])

            files = os.listdir(self.input_dir)
            files = [f for f in files if f.endswith('.abf')]  # only abf files

            if len(files) == 0:
                continue  # no abf files, keep waiting

            last_modified = [os.path.getmtime(os.path.join(self.input_dir, f)) for f in files]
            latest_mod_time = dt.fromtimestamp(np.max(last_modified))

            if latest_mod_time < self._start_time + timedelta(seconds=self.settings['wait_time']):
                continue  # no new files, keep waiting

            latest_file = files[np.argmax(last_modified)]

            self.analyse_rec(os.path.join(self.input_dir, latest_file))

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
        if not os.path.isfile(file2analyse):
            raise FileNotFoundError(
                f"ABF file not found: '{file2analyse}'. "
                f"Please check the file path."
            )

        only_filename = os.path.splitext(os.path.basename(file2analyse))[0]
        if len(self.sweeps2analyse) == self.n_sweeps:
            logger.info("Starting analysis of '%s'...", only_filename)
            self._fig_list = []

        # TODO: CURRENTLY ONLY ONE ANALYSIS TYPE
        analyse_function = get_analysis_function(self.analysis['type'][0])
        analyse_kwargs = set_analysis_parameters(self.analysis['type'][0], **self.__dict__)

        abf_file = ABF(file2analyse)

        # read (meta) data
        x_time = abf_file.sweepX
        sampling_rate = abf_file.dataRate

        if sampling_rate != self.sampling_rate:
            raise ValueError(
                f"Sampling rate mismatch in '{file2analyse}': "
                f"expected {self.sampling_rate} Hz, got {sampling_rate} Hz. "
                f"Please check the recording settings."
            )

        for c_sweep in abf_file.sweepList:
            if c_sweep not in self.sweeps2analyse:
                continue
            else:  # go through every sweep only once
                self.sweeps2analyse.remove(c_sweep)

            abf_file.setSweep(c_sweep)
            sweep_trace = abf_file.sweepY

            self._fig_list.append(
                analyse_function(
                    x_time,
                    sweep_trace,
                    sweep_number=c_sweep,
                    **analyse_kwargs,  # ensure named arguments are passed
                    **self.__dict__['analysis']['visualisation'],  # used for visualisation settings
                )
            )

            with PdfPages(os.path.join(self.analysis_dir, f'{only_filename}.pdf')) as pdf:
                for fig in self._fig_list:  # save all figures in one pdf
                    pdf.savefig(fig)

        return len(self.sweeps2analyse)
