"""Welcome to the PynamicGain package!

To avoid having an util module, functions used by multiple modules are stored here.
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


import os
import time
from datetime import datetime as dt
from datetime import timedelta
from importlib.metadata import version, PackageNotFoundError
from typing import Optional

try:
    __version__ = version("pynamicgain")
except PackageNotFoundError:
    __version__ = "unknown"

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tomli
import tomli_w
from matplotlib.backends.backend_pdf import PdfPages
from numpy.random import PCG64DXSM
from pyabf import ABF
from pyabf.abfWriter import writeABF1
from tqdm import tqdm

from pynamicgain.stimulus_generation import generate_input, create_filename
from pynamicgain.analysis import get_analysis_function, set_analysis_parameters


def config_header(read_configs: dict) -> str:
    """Create the header of the configuration file.

    Since tomli_w does not support comments, the header is created manually.
    Some configuration information (e.g. the setup id) is already stored in
    the header and will therefore be read from the current configurations.

    Args:
        read_configs: The current configurations saved as dict.

    Returns:
        The header string for the configuration file.
    """
    header = (
        f'# Configuration File for DG PClamp Setup {read_configs["setup_id"]}\n'
        '# =========================================\n\n'
        
        '# ========================================================================= #\n'
        '# ! NOTE: DO NOT COPY THIS FILE FROM ONE SETUP TO THE OTHER! THIS IS No'
        f'{read_configs["setup_id"]} !  #\n'
        '# ========================================================================= #\n\n'
        
        f'# This file was created by {read_configs["config_file_creator"]}.\n'
        f'# Creation date: {read_configs["creation_time"]}\n\n'
        
        '# Author: Friedrich Schwarz <friedrichschwarz@unigoettingen.de>\n'
        '# Please contact the author if you have any problems (or suggestions).\n\n'
    )
    return header


def read_setup_configs(setup_dir: str) -> tuple[str, dict]:
    """Read the setup configuration file and return the configurations.

    Searches for the setup file in the given directory, then reads
    the configurations from the file.

    Args:
        setup_dir: The directory where the setup file is stored.

    Returns:
        A tuple of (setup_file_path, configurations_dict).

    Raises:
        AssertionError: If not exactly one setup file is found.
    """
    setup_file = [f for f in os.listdir(setup_dir) if f.startswith('setup_')]
    assert len(setup_file) == 1, f"ABORT: Expected exactly one setup file, found {len(setup_file)}!"
    
    setup_file = os.path.join(setup_dir, setup_file[0])
    with open(setup_file, 'rb') as f:
        setup_configs = tomli.load(f)
        
    return setup_file, setup_configs


class PyDGBase:
    """Base class for the PynamicGain package.

    Reads the setup configurations and parses CLI arguments. All specified
    directories will be created if they do not exist. Instance attributes
    are set dynamically from the setup configurations and CLI arguments.

    Private attributes (prefixed with ``_``) will not be written to the
    setup file.

    Attributes:
        _setup_file: The path to the setup file.
        _setup_configs: The configurations stored in the setup file.
        setup_dir: The directory where the setup file is stored.
        version: The version of the PynamicGain package.
        master_seed: The master seed for the random number generator.
        n_seeds_per_setup: The number of seeds per setup.
        current_seed_index: The current seed index.
        setup_id: The setup id.
        setup_info: The setup description.
        config_file_creator: The creator of the setup file.
        creation_time: The creation time of the setup file.
        stimulus_type: The type of stimulus to generate.
        n_sweeps: The number of sweeps to generate.
        duration: The duration of the sweeps in seconds.
        sampling_rate: The sampling rate of the recordings in Hz.
    """

    def __init__(self, cli_args: dict):
        """Initialise from setup configurations and CLI arguments.

        Args:
            cli_args: Dictionary of command line arguments.
        """
        self._setup_file, self._setup_configs = read_setup_configs(cli_args['setup_dir'])
        cli_args.update(self._setup_configs)

        for k, v in cli_args.items():
            setattr(self, k, v)
            if 'dir' in k:
                if 'backup' in k and v == '':
                    setattr(self, k, os.path.join(cli_args['out_dir'], 'backup'))
                    os.makedirs(self.backup_dir, exist_ok=True)
                    continue
                elif 'analysis' in k and v == '':
                    setattr(self, k, os.path.join(cli_args['input_dir'], 'analysis'))
                    os.makedirs(self.analysis_dir, exist_ok=True)
                    continue
                os.makedirs(v, exist_ok=True)

    def __repr__(self):
        """Return a detailed string representation with all attributes."""
        attrs = '\n\t'.join(f"{k + ': ': <25}{v!r}" for k, v in self.__dict__.items())
        return f'\n{self.__class__.__name__}:\n\t{attrs}'

    def __str__(self):
        """Return a human-readable string representation."""
        return self.__repr__()


class PyDG(PyDGBase):
    """Main class for generating DG inputs and analysing recordings.

    .. inheritance-diagram:: pynamicgain.__init__.PyDG
        :parts: 1

    Attributes:
        std: The standard deviation of the input signal.
        corr_t: The correlation time of the input signal.
        out_dir: The directory where generated files will be stored.
        backup_dir: The directory where backup files will be stored.
        _seed_csv: The path to the seed list CSV file.
        _bg: The PCG64DXSM random number generator.
    """

    def __init__(self, cli_args: dict):
        """Initialise from setup configurations and CLI arguments.

        Args:
            cli_args: Dictionary of command line arguments.
        """
        super().__init__(cli_args)

        self._seed_csv = os.path.join(cli_args['setup_dir'], f'seed_list_setup_{self._setup_configs["setup_id"]}.csv')
        
        if not self.backup_dir:
            self.backup_dir = os.path.join(self.out_dir, 'backup')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        self._bg = PCG64DXSM(self.master_seed)
        self._bg.advance(self.current_seed_index + self.setup_id * self.n_seeds_per_setup)
    
    def return_setup_configs_from_attr(self) -> dict:
        """Return all non-private configurations as a dictionary.

        Returns:
            Dictionary of public instance attributes (keys not starting
            with ``_``).
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def new_seed(self) -> int:
        """Advance the seed index, persist it, and return a new seed.

        To ensure no seed is used twice, the seed index is updated
        before generating new inputs. The sequence is:

        1. Increase seed index in the instance.
        2. Persist the updated index to the setup file.
        3. Draw a new seed from the RNG.
        4. Append the new seed to the CSV log.
        5. Return the new seed for input generation.

        Returns:
            The new seed for the next input generation.

        Raises:
            RuntimeError: If any step of the seed update process fails.
        """
        try:
            self.current_seed_index += 1  # increase seed index in class
            
            # update setup file
            with open(self._setup_file, 'w') as f:
                f.write(config_header(self.__dict__))
                f.write(tomli_w.dumps(self.return_setup_configs_from_attr()))
            
            new_seed = self._bg.random_raw()  # draw new seed
            
            # save new seed in csv
            df_ = pd.read_csv(
                self._seed_csv,
                index_col=False,
                header=0,
            )
            
            df_new = pd.DataFrame(
                [{
                    'seed index': self.current_seed_index,
                    'seed': new_seed,
                    'sweep': self._c_sweep,
                    'file': self._f_path_name,
                    'backup': self._b_path_name, 
                }]
            )
            
            df = pd.concat([df_, df_new], axis=0)
            df.to_csv(self._seed_csv, index=False)
            
            return new_seed
        
        except Exception as e:  
            # just to be sure, that the program does stop
            raise RuntimeError(f"Error while updating seed: {e}")

    def create_input_abf(self) -> dt:
        """Create all input sweeps and write them to an ABF file.

        A backup copy of the ABF file is also written to the backup
        directory with a timestamp prefix.

        Returns:
            The timestamp marking the start of input generation
            (used to schedule analysis).
        """
        self._f_name = create_filename(self.stimulus_type, **self.__dict__)
        self._f_path_name = os.path.join(self.out_dir, self._f_name)
        
        # the backup file will be written into the backup directory
        # a timestamp is added as prefix to the filename
        _pts = dt.now()
        self._b_name = f'{_pts.strftime("%Y%m%d_%H%M%S")}_{self._f_name}'
        self._b_path_name = os.path.join(self.backup_dir, self._b_name)
        
        sweep_list = []
        for i in tqdm(range(int(self.n_sweeps)), desc='Creating input sweeps'):
            self._c_sweep = i
            
            sweep_list.append(
                generate_input(
                    self.stimulus_type, 
                    key=self.new_seed(), 
                    **self.__dict__
                )  # shape: (n_samples,)
            )

        input_array = np.array(sweep_list)  # shape: (n_sweeps, n_samples)
        
        for _sp in tqdm([self._f_path_name, self._b_path_name], desc='Writing ABF files'):
            writeABF1(input_array, _sp, float(self.sampling_rate), units=self.settings['input_units'])
        
        return _pts  # for calc delay of start analysis


class PyDGAnalysis(PyDGBase):
    """Analysis class for the dynamic gain calculations.

    .. inheritance-diagram:: pynamicgain.__init__.PyDGAnalysis
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
            self._observation_duration = self.n_sweeps * self.duration + 180  # 3 minutes buffer
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
        print(f'Start observing {self.input_dir} for new files to analyse...')
        while dt.now() < self._max_time:
            time.sleep(self.settings['update_interval'])
            
            files = os.listdir(self.input_dir)
            files = [f for f in files if f.endswith('.abf')]  # only abf files
            
            if len(files) == 0:
                continue  # no abf files, keep waiting
            
            last_modified= [os.path.getmtime(os.path.join(self.input_dir, f)) for f in files]
            latest_mod_time = dt.fromtimestamp(np.max(last_modified))
            
            if latest_mod_time < self._start_time + timedelta(seconds=self.settings['wait_time']):
                continue  # no new files, keep waiting
            
            latest_file = files[np.argmax(last_modified)]
            
            self.analyse_rec(os.path.join(self.input_dir, latest_file))
            
            if len(self.sweeps2analyse) == 0:
                plt.close('all')
                break
        
        if len(self.sweeps2analyse) > 0:
            print(f'Not all sweeps analysed. Remaining sweeps: {self.sweeps2analyse}')
            
        return len(self.sweeps2analyse)


    def analyse_rec(self, file2analyse: str) -> int:
        """Analyse all available sweeps in a single ABF file.

        Can be called explicitly to analyse existing data or by the
        observer to analyse newly recorded data.

        Args:
            file2analyse: Absolute path to the ABF file to analyse.

        Returns:
            The number of sweeps that remain unanalysed.

        Note:
            ABF sweeps cannot be read concurrently. The current sweep is
            selected via ``abf.setSweep`` and its data accessed through
            ``abf.sweepY``. The full sweep list is in ``abf.sweepList``.
        """
        only_filename = os.path.splitext(os.path.basename(file2analyse))[0]
        if len(self.sweeps2analyse) == self.n_sweeps:
            print(f'\nStarting analysis of {only_filename} ...\n')
            self._fig_list = []

        # TODO: CURRENTLY ONLY ONE ANALYSIS TYPE
        analyse_function = get_analysis_function(self.analysis['type'][0])
        analyse_kwargs = set_analysis_parameters(self.analysis['type'][0], **self.__dict__)

        abf_file = ABF(file2analyse)

        # read (meta) data
        x_time = abf_file.sweepX
        sampling_rate = abf_file.dataRate
        assert sampling_rate == self.sampling_rate, "Sample rate mismatch"

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
