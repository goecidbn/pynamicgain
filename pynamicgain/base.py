"""Base class for the PynamicGain package.

Provides the shared initialisation logic for both the generator
(:class:`~pynamicgain.generator.PyDG`) and the analysis observer
(:class:`~pynamicgain.observer.PyDGAnalysis`).
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
from abc import ABC

from pynamicgain.config import read_setup_configs, check_directory


class PyDGBase(ABC):
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
                    check_directory(self.backup_dir, 'backup')
                    continue
                elif 'analysis' in k and v == '':
                    setattr(self, k, os.path.join(cli_args['input_dir'], 'analysis'))
                    check_directory(self.analysis_dir, 'analysis')
                    continue
                check_directory(v, k)

    def __repr__(self):
        """Return a detailed string representation with all attributes."""
        attrs = '\n\t'.join(f"{k + ': ': <25}{v!r}" for k, v in self.__dict__.items())
        return f'\n{self.__class__.__name__}:\n\t{attrs}'

    def __str__(self):
        """Return a human-readable string representation."""
        return self.__repr__()
