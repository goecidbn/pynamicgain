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


__version__ = '0.0.10'


import os
import time
from datetime import datetime as dt
from datetime import timedelta
from typing import Optional

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
    """Returns the header of the configuration file.

    Since tomli_w does not support comments, the header is created manually.
    
    Some configuration information (e.g. the setup id) is already stored in
    the header and will therefore be read from the current configurations.

    Args:
        read_configs (dict): The current configurations saved as dict.

    Returns:
        str: The header for the configuration file.
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
    """Reads the setup configuration file and returns the configurations as dict.
    
    First, searches for the setup file in the given directory. Then, reads the
    configurations from the file.
    
    Args:
        setup_dir (str): The directory where the setup file is stored.
        
    Returns:
        tuple[str, dict]: A tuple of the setup file path and the configurations dict.
    """
    setup_file = [f for f in os.listdir(setup_dir) if f.startswith('setup_')]
    assert len(setup_file) == 1, f"ABORT: Expected exactly one setup file, found {len(setup_file)}!"
    
    setup_file = os.path.join(setup_dir, setup_file[0])
    with open(setup_file, 'rb') as f:
        setup_configs = tomli.load(f)
        
    return setup_file, setup_configs


class PyDGBase:
    """Base class for the PynamicGain package.
    
    This class is responsible for reading the setup configurations and parsing
    the command line arguments.
    
    All specified directories will be created if they do not exist.
    
    The instance attributes are set dynamically from the setup configurations
    and the command line arguments.
    
    All private attributes are stored with an underscore in the beginning and
    will not be written to the setup file.
    
    The following attributes will be set:
        - _setup_file (str): The path to the setup file.
        - _setup_configs (dict): The configurations stored in the setup file.
        - setup_dir (str): The directory where the setup file is stored.
        - version (str): The version of the PynamicGain package.
        - master_seed (int): The master seed for the random number generator.
        - n_seeds_per_setup (int): The number of seeds per setup.
        - current_seed_index (int): The current seed index.
        - setup_id (int): The setup id.
        - setup_info (str): The setup description.
        - config_file_creator (str): The creator of the setup file.
        - creation_time (str): The creation time of the setup file.
        - stimulus_type (str): The type of stimulus to generate.
        - n_sweeps (int): The number of sweeps to generate.
        - duration (float): The duration of the sweeps.
        - sampling_rate (int): The sampling rate of the recordings.
    
    """
    
    def __init__(self, cli_args: dict):
        """Read setup configurations and command line arguments set them as attributes."""
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
        """Create a string representation of the class (every attribute with its value in a new line)"""
        attrs = '\n\t'.join(f"{k + ': ': <25}{v!r}" for k, v in self.__dict__.items())
        return f'\n{self.__class__.__name__}:\n\t{attrs}'

    def __str__(self):
        """Create a string representation of the class (every attribute with its value in a new line)"""
        return self.__repr__()


class PyDG(PyDGBase):
    """Main class for the PynamicGain package for generating DG inputs and analysing recordings.
    
    .. inheritance-diagram:: pynamicgain.__init__.PyDG
        :parts: 1
        
    The following additional instance attributes are set:
        - std (float): The standard deviation of the input signal. 
        - corr_t (float): The correlation time of the input signal.
        - out_dir (str): The directory where generated files will be stored.
        - backup_dir (str): The directory where backup files will be stored.
        - _seed_csv (str): The path to the seed list csv file.
        - _bg (PCG64DXSM): The random number generator.
    
    """
     
    def __init__(self, cli_args: dict):
        """Read setup configurations and command line arguments set them as attributes"""
        super().__init__(cli_args)

        self._seed_csv = os.path.join(cli_args['setup_dir'], f'seed_list_setup_{self._setup_configs["setup_id"]}.csv')
        
        if not self.backup_dir:
            self.backup_dir = os.path.join(self.out_dir, 'backup')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        self._bg = PCG64DXSM(self.master_seed)
        self._bg.advance(self.current_seed_index + self.setup_id * self.n_seeds_per_setup)
    
    def return_setup_configs_from_attr(self):
        """Return all non-private configurations as dict."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def new_seed(self) -> int:
        """Update the seed index in the class and the setup file.
        
        To ensure no seed is used twice, all updating of the seed index is done
        before generating new inputs.
        
        Order:
            - increase seed index in class
            - update seed index in setup file
            - draw new seed
            - save new seed in csv
            - return new seed (to further use for input generation)
            
        Returns:
            int: The new seed for the next input generation.
            
        Raises:
            RuntimeError: If an error occurs during the seed update process.
            
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

    def create_input_abf(self):
        """Creates all input traces and writes them to an ABF file.
        
        Furthermore, a backup file is created in the backup directory.
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
    """Basic analysis class for the dynamic gain calculations.
    
    .. inheritance-diagram:: pynamicgain.__init__.PyDGAnalysis
        :parts: 1  
        
    The following additional instance attributes are set:
        - _start_time (dt): The start time for the observation.
        - _max_time (dt): The maximum time for the observation.
        - _observation_duration (int): The estimated duration of recording plus buffer.
        - sweeps2analyse (list): The sweeps that still need to be analysed.
        - input_dir (str): The directory where to watch for new recordings.
        - analysis_dir (str): The directory where the analysis results will be stored.
        - analysis (dict): The analysis setting (including visualisation settings).
    
    """
    
    def __init__(self, cli_args: dict, start_time: Optional[dt] = None) -> None:
        """Read setup configurations and command line arguments set them as attributes."""
        super().__init__(cli_args)

        if start_time:
            self._start_time = start_time
            self._observation_duration = self.n_sweeps * self.duration + 180  # 3 minutes buffer
            self._max_time = start_time + timedelta(seconds=self._observation_duration)

        else:
            self._start_time = self._max_time = None
            
        self.sweeps2analyse = list(np.arange(self.n_sweeps, dtype=int))

    def observe(self):
        """Observe a directory and analyse newly generated data."""
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


    def analyse_rec(self, file2analyse: str):
        """Wrapper to analyse newly generated data.
        
        This function analyses all available sweeps in one abf file. When called
        explicitly, it can be used to analyse old data. However, this function
        is also used by the observer to analyse the latest data.

        Args:
            what (list, optional): The type of analysis to perform. Defaults to
            ['mini_sta'].

        Returns:
            dict: The results of the analysis.

        Note:
            The sweeps of the abf file can not be read concurrently. Therefore, one
            must iterate through all sweeps. The variable storing the current sweep
            can be set via `abf.SetSweep`. Initially, the first sweep is set
            automatically. The sweep data is stored in `abf.sweepY`. All sweeps are
            stored in `abf.sweepList`.
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
