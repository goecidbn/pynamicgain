"""Stimulus generation orchestration for the PynamicGain package.

Contains :class:`PyDG`, the main class responsible for seed management,
sweep generation, and ABF file output.
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
from datetime import datetime as dt

import numpy as np
import pandas as pd
import tomli_w
from numpy.random import PCG64DXSM
from pyabf.abfWriter import writeABF1
from tqdm import tqdm

from pynamicgain.base import PyDGBase
from pynamicgain.config import config_header, check_directory
from pynamicgain.stimulus_generation import generate_input, create_filename

logger = logging.getLogger(__name__)


class PyDG(PyDGBase):
    """Main class for generating DG inputs and analysing recordings.

    .. inheritance-diagram:: pynamicgain.generator.PyDG
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
        check_directory(self.backup_dir, 'backup')

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
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=setup_dir, suffix='.toml.tmp')
            with os.fdopen(fd, 'w') as f:
                f.write(config_header(self.__dict__))
                f.write(tomli_w.dumps(self.return_setup_configs_from_attr()))
            os.replace(tmp_path, self._setup_file)
        except OSError as e:
            # Clean up temp file if replace failed
            if tmp_path and os.path.exists(tmp_path):
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
