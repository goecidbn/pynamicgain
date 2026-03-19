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


import csv
import logging
import os
import tempfile
import time
from abc import ABC
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

logger = logging.getLogger(__name__)

# Required top-level keys and their expected types for config validation
_REQUIRED_CONFIG_KEYS = {
    'version': str,
    'master_seed': int,
    'n_seeds_per_setup': int,
    'current_seed_index': int,
    'setup_id': int,
    'setup_info': str,
    'config_file_creator': str,
    'creation_time': str,
    'stimulus_type': str,
}


def setup_logging(level: str = "INFO") -> None:
    """Configure the package-level logger.

    Sets up a console handler with a timestamped formatter. Should be
    called once at application startup (e.g. from the CLI entry points).

    Args:
        level: Logging level string. One of ``'DEBUG'``, ``'INFO'``,
            ``'WARNING'``, ``'ERROR'``, ``'CRITICAL'``. Defaults to
            ``'INFO'``.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    pkg_logger = logging.getLogger("pynamicgain")
    if pkg_logger.handlers:
        return  # already configured
    pkg_logger.setLevel(numeric_level)
    handler = logging.StreamHandler()
    handler.setLevel(numeric_level)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    handler.setFormatter(formatter)
    pkg_logger.addHandler(handler)


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


def validate_setup_configs(configs: dict) -> None:
    """Validate that a setup configuration dict contains all required keys.

    Args:
        configs: Configuration dictionary loaded from a TOML file.

    Raises:
        ValueError: If a required key is missing or has the wrong type.
    """
    for key, expected_type in _REQUIRED_CONFIG_KEYS.items():
        if key not in configs:
            raise ValueError(
                f"Configuration file is missing required key '{key}'. "
                f"Please regenerate the config with 'pydg_new_setup' or add the key manually."
            )
        if not isinstance(configs[key], expected_type):
            raise TypeError(
                f"Configuration key '{key}' must be of type {expected_type.__name__}, "
                f"got {type(configs[key]).__name__}."
            )

    if configs['setup_id'] < 1:
        raise ValueError(
            f"setup_id must be a positive integer, got {configs['setup_id']}."
        )
    if configs['n_seeds_per_setup'] < 1:
        raise ValueError(
            f"n_seeds_per_setup must be a positive integer, got {configs['n_seeds_per_setup']}."
        )
    if configs['current_seed_index'] < 0:
        raise ValueError(
            f"current_seed_index must be non-negative, got {configs['current_seed_index']}."
        )


def read_setup_configs(setup_dir: str) -> tuple[str, dict]:
    """Read the setup configuration file and return the configurations.

    Searches for the setup file in the given directory, then reads and
    validates the configurations from the file.

    Args:
        setup_dir: The directory where the setup file is stored.

    Returns:
        A tuple of (setup_file_path, configurations_dict).

    Raises:
        FileNotFoundError: If the setup directory does not exist or
            contains no setup file.
        ValueError: If more than one setup file is found, or if the
            configuration is missing required keys.
    """
    if not os.path.isdir(setup_dir):
        raise FileNotFoundError(
            f"Setup directory does not exist: '{setup_dir}'. "
            f"Please check the --setup_dir argument."
        )

    setup_file = [f for f in os.listdir(setup_dir) if f.startswith('setup_')]

    if len(setup_file) == 0:
        raise FileNotFoundError(
            f"No setup file found in '{setup_dir}'. "
            f"Please run 'pydg_new_setup' first to create a setup configuration."
        )
    if len(setup_file) > 1:
        raise ValueError(
            f"Expected exactly one setup file in '{setup_dir}', "
            f"found {len(setup_file)}: {setup_file}. "
            f"Each setup directory must contain only one setup_*.toml file."
        )

    setup_file = os.path.join(setup_dir, setup_file[0])
    try:
        with open(setup_file, 'rb') as f:
            setup_configs = tomli.load(f)
    except tomli.TOMLDecodeError as e:
        raise ValueError(
            f"Failed to parse setup file '{setup_file}': {e}. "
            f"The file may be corrupted. Please check the TOML syntax."
        ) from e

    validate_setup_configs(setup_configs)
    logger.info("Loaded setup configuration from '%s'.", setup_file)

    return setup_file, setup_configs


def _check_directory(path: str, name: str) -> None:
    """Create a directory and verify write permissions.

    Args:
        path: The directory path to create/check.
        name: Human-readable name for error messages (e.g. ``'output'``).

    Raises:
        PermissionError: If the directory cannot be created or is not
            writable.
    """
    try:
        os.makedirs(path, exist_ok=True)
    except PermissionError:
        raise PermissionError(
            f"Cannot create {name} directory '{path}': permission denied. "
            f"Please check the file system permissions."
        )
    if not os.access(path, os.W_OK):
        raise PermissionError(
            f"The {name} directory '{path}' is not writable. "
            f"Please check the file system permissions."
        )


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
                    _check_directory(self.backup_dir, 'backup')
                    continue
                elif 'analysis' in k and v == '':
                    setattr(self, k, os.path.join(cli_args['input_dir'], 'analysis'))
                    _check_directory(self.analysis_dir, 'analysis')
                    continue
                _check_directory(v, k)

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

        Recovers ``current_seed_index`` from the seed CSV if it exists
        (CSV is the single source of truth). The TOML file is updated
        for informational purposes only.

        Args:
            cli_args: Dictionary of command line arguments.
        """
        super().__init__(cli_args)

        self._seed_csv = os.path.join(
            cli_args['setup_dir'],
            f'seed_list_setup_{self._setup_configs["setup_id"]}.csv',
        )

        # Recover seed index from CSV (single source of truth)
        self._reconcile_seed_index()

        if not self.backup_dir:
            self.backup_dir = os.path.join(self.out_dir, 'backup')
        _check_directory(self.backup_dir, 'backup')

        self._bg = PCG64DXSM(self.master_seed)
        self._bg.advance(self.current_seed_index + self.setup_id * self.n_seeds_per_setup)

    def _reconcile_seed_index(self) -> None:
        """Reconcile seed index from the CSV file (source of truth).

        If the CSV exists and contains entries, the maximum seed index
        is used as the authoritative value. The in-memory attribute and
        the TOML file are updated accordingly.

        Raises:
            FileNotFoundError: If the seed CSV file does not exist.
        """
        if not os.path.isfile(self._seed_csv):
            raise FileNotFoundError(
                f"Seed CSV file not found: '{self._seed_csv}'. "
                f"Please run 'pydg_new_setup' to create a new setup, "
                f"or check the setup directory."
            )

        try:
            df = pd.read_csv(self._seed_csv, index_col=False, header=0)
        except pd.errors.EmptyDataError:
            logger.debug("Seed CSV is empty (header only). Starting at index 0.")
            return
        except Exception as e:
            raise RuntimeError(
                f"Failed to read seed CSV '{self._seed_csv}': {e}. "
                f"The file may be corrupted. Please check the CSV manually "
                f"or contact the developer."
            ) from e

        if len(df) > 0 and 'seed index' in df.columns:
            csv_index = int(df['seed index'].max())
            if csv_index != self.current_seed_index:
                logger.warning(
                    "Seed index mismatch: TOML has %d, CSV has %d. "
                    "Using CSV value (source of truth).",
                    self.current_seed_index, csv_index,
                )
                self.current_seed_index = csv_index
                self._persist_setup_file()

    def return_setup_configs_from_attr(self) -> dict:
        """Return all non-private configurations as a dictionary.

        Returns:
            Dictionary of public instance attributes (keys not starting
            with ``_``).
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def _persist_setup_file(self) -> None:
        """Atomically write the setup TOML file via a temp file.

        Writes to a temporary file in the same directory, then performs
        an atomic ``os.replace`` to avoid partial writes.

        Raises:
            OSError: If the file cannot be written.
        """
        setup_dir = os.path.dirname(self._setup_file)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=setup_dir, suffix='.toml.tmp')
            with os.fdopen(fd, 'w') as f:
                f.write(config_header(self.__dict__))
                f.write(tomli_w.dumps(self.return_setup_configs_from_attr()))
            os.replace(tmp_path, self._setup_file)
        except OSError as e:
            # Clean up temp file if replace failed
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise OSError(
                f"Failed to write setup file '{self._setup_file}': {e}. "
                f"Please check disk space and permissions."
            ) from e

    def _advance_seed(self) -> tuple[int, int]:
        """Advance the seed index and draw a new seed from the RNG.

        This method only mutates in-memory state. Persistence is handled
        separately by :meth:`_log_seeds`.

        Returns:
            A tuple of ``(new_seed_index, new_seed)``.
        """
        self.current_seed_index += 1
        new_seed = self._bg.random_raw()
        return self.current_seed_index, new_seed

    def _log_seeds(self, seed_records: list[dict]) -> None:
        """Append seed records to the CSV and persist the setup file.

        Uses append-only CSV writes and atomic TOML replacement to
        ensure consistency. The CSV is the single source of truth for
        seed tracking; the TOML ``current_seed_index`` is updated for
        informational purposes.

        Args:
            seed_records: List of dicts with keys ``'seed index'``,
                ``'seed'``, ``'sweep'``, ``'file'``, ``'backup'``.

        Raises:
            OSError: If the CSV file cannot be written.
            RuntimeError: If an unexpected error occurs during seed
                logging. Contact the developer.
        """
        if not seed_records:
            return

        try:
            with open(self._seed_csv, 'a', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['seed index', 'seed', 'sweep', 'file', 'backup'],
                )
                for record in seed_records:
                    writer.writerow(record)
            logger.debug(
                "Appended %d seed record(s) to '%s'.",
                len(seed_records), self._seed_csv,
            )
        except PermissionError:
            raise PermissionError(
                f"Cannot write to seed CSV '{self._seed_csv}': permission denied."
            )
        except OSError as e:
            raise OSError(
                f"Failed to append to seed CSV '{self._seed_csv}': {e}. "
                f"Please check disk space and file system integrity."
            ) from e

        # Update TOML for informational purposes
        try:
            self._persist_setup_file()
        except OSError:
            logger.warning(
                "Seeds were logged to CSV but TOML update failed. "
                "The CSV remains the source of truth."
            )

    def create_input_abf(self) -> dt:
        """Create all input sweeps and write them to an ABF file.

        Generates all sweeps, draws seeds via :meth:`_advance_seed`, and
        logs all seed records in a single batch via :meth:`_log_seeds`.
        A backup copy of the ABF file is also written to the backup
        directory with a timestamp prefix.

        Returns:
            The timestamp marking the start of input generation
            (used to schedule analysis).

        Raises:
            RuntimeError: If input generation or file writing fails.
        """
        f_name = create_filename(self.stimulus_type, **self.__dict__)
        f_path_name = os.path.join(self.out_dir, f_name)

        # the backup file will be written into the backup directory
        # a timestamp is added as prefix to the filename
        _pts = dt.now()
        b_name = f'{_pts.strftime("%Y%m%d_%H%M%S")}_{f_name}'
        b_path_name = os.path.join(self.backup_dir, b_name)

        sweep_list = []
        seed_records = []

        try:
            for i in tqdm(range(int(self.n_sweeps)), desc='Creating input sweeps'):
                seed_index, seed = self._advance_seed()
                seed_records.append({
                    'seed index': seed_index,
                    'seed': seed,
                    'sweep': i,
                    'file': f_path_name,
                    'backup': b_path_name,
                })
                sweep_list.append(
                    generate_input(
                        self.stimulus_type,
                        key=seed,
                        **self.__dict__
                    )  # shape: (n_samples,)
                )
        except Exception as e:
            raise RuntimeError(
                f"Sweep generation failed at sweep {i}: {e}. "
                f"No seeds have been persisted. Please check the stimulus parameters "
                f"and contact the developer if the problem persists."
            ) from e

        input_array = np.array(sweep_list)  # shape: (n_sweeps, n_samples)

        for _sp in tqdm([f_path_name, b_path_name], desc='Writing ABF files'):
            try:
                writeABF1(input_array, _sp, float(self.sampling_rate), units=self.settings['input_units'])
            except OSError as e:
                raise OSError(
                    f"Failed to write ABF file '{_sp}': {e}. "
                    f"Please check disk space and permissions."
                ) from e

        # Persist all seeds in one batch after successful ABF write
        self._log_seeds(seed_records)
        logger.info(
            "Generated %d sweeps -> '%s' (backup: '%s').",
            self.n_sweeps, f_path_name, b_path_name,
        )

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
