"""Stimulus generation orchestration for the PynamicGain package.

Contains :class:`PyDG`, the main class responsible for seed management,
sweep generation, and ABF file output.

.. versionchanged:: 0.1.0
   ``PyDG`` no longer inherits from ``PyDGBase``. It uses composition
   with :class:`~pynamicgain.seed.SeedManager` and accepts a
   :class:`~pynamicgain._types.SetupConfig` directly.
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
from datetime import datetime as dt
from typing import Union

import numpy as np
from pyabf.abfWriter import writeABF1
from tqdm import tqdm

from pynamicgain._types import SetupConfig
from pynamicgain.config import load_config, check_directory
from pynamicgain.seed import SeedManager
from pynamicgain.stimulus_generation import (
    generate_input,
    generate_input_from_params,
    build_stimulus_params,
    create_filename,
    create_filename_from_config,
)

logger = logging.getLogger(__name__)


class PyDG:
    """Main class for generating DG inputs.

    .. versionchanged:: 0.1.0
       Uses composition instead of inheriting from ``PyDGBase``.
       Accepts either a :class:`SetupConfig` or a legacy ``cli_args``
       dict for backwards compatibility.

    Attributes:
        config: The frozen setup configuration.
        seed_manager: The seed manager handling RNG state and persistence.
    """

    def __init__(self, cli_args_or_config: Union[dict, SetupConfig]) -> None:
        """Initialise from a config or legacy CLI args dict.

        Args:
            cli_args_or_config: Either a :class:`SetupConfig` instance
                (preferred) or a dict of CLI arguments (legacy path).
        """
        if isinstance(cli_args_or_config, SetupConfig):
            self.config = cli_args_or_config
        else:
            # Legacy path: build config from CLI args dict
            self.config = load_config(cli_args_or_config)

        self.seed_manager = SeedManager(self.config)

        # Ensure backup directory exists
        if self.config.backup_dir:
            check_directory(self.config.backup_dir, 'backup')

        # Backwards compatibility: expose config fields as instance attrs
        # so that old code accessing self.n_sweeps, self.out_dir, etc. still works
        for field in dataclasses.fields(self.config):
            if not hasattr(self, field.name):
                setattr(self, field.name, getattr(self.config, field.name))

        # Legacy aliases used by old code
        self._setup_file = self.config.setup_file
        self._setup_configs = dataclasses.asdict(self.config)
        self._seed_csv = self.config.seed_csv

    def __repr__(self) -> str:
        """Return a detailed string representation with all config fields."""
        attrs = '\n\t'.join(
            f"{f.name + ': ': <25}{getattr(self.config, f.name)!r}"
            for f in dataclasses.fields(self.config)
        )
        return f'\n{self.__class__.__name__}:\n\t{attrs}'

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return self.__repr__()

    def return_setup_configs_from_attr(self) -> dict:
        """Return all configuration fields as a dictionary.

        Returns:
            Dictionary of configuration fields.
        """
        d = dataclasses.asdict(self.config)
        d['current_seed_index'] = self.seed_manager.current_index
        # Remove internal path fields not part of the TOML
        for key in ('setup_dir', 'setup_file', 'seed_csv', 'std', 'corr_t'):
            d.pop(key, None)
        return d

    def create_input_abf(self) -> dt:
        """Create all input sweeps and write them to an ABF file.

        Generates all sweeps, draws seeds via the seed manager, and
        logs all seed records in a single batch after successful file
        writing. A backup copy of the ABF file is also written.

        Returns:
            The timestamp marking the start of input generation
            (used to schedule analysis).

        Raises:
            RuntimeError: If input generation or file writing fails.
        """
        cfg = self.config

        f_name = create_filename_from_config(cfg)
        f_path_name = os.path.join(cfg.out_dir, f_name)

        _pts = dt.now()
        b_name = f'{_pts.strftime("%Y%m%d_%H%M%S")}_{f_name}'
        b_path_name = os.path.join(cfg.backup_dir, b_name)

        sweep_list = []
        seed_records = []

        try:
            for i in tqdm(range(int(cfg.n_sweeps)), desc='Creating input sweeps'):
                seed_index, seed = self.seed_manager.draw()
                seed_records.append({
                    'seed index': seed_index,
                    'seed': seed,
                    'sweep': i,
                    'file': f_path_name,
                    'backup': b_path_name,
                })
                stim_params = build_stimulus_params(cfg, key=seed)
                sweep_list.append(generate_input_from_params(stim_params))
        except Exception as e:
            raise RuntimeError(
                f"Sweep generation failed at sweep {i}: {e}. "
                f"No seeds have been persisted. Please check the stimulus parameters "
                f"and contact the developer if the problem persists."
            ) from e

        input_array = np.array(sweep_list)  # shape: (n_sweeps, n_samples)

        input_units = cfg.settings.get('input_units', 'pA')
        for _sp in tqdm([f_path_name, b_path_name], desc='Writing ABF files'):
            try:
                writeABF1(input_array, _sp, float(cfg.sampling_rate), units=input_units)
            except OSError as e:
                raise OSError(
                    f"Failed to write ABF file '{_sp}': {e}. "
                    f"Please check disk space and permissions."
                ) from e

        # Persist all seeds in one batch after successful ABF write
        self.seed_manager.commit(seed_records)
        logger.info(
            "Generated %d sweeps -> '%s' (backup: '%s').",
            cfg.n_sweeps, f_path_name, b_path_name,
        )

        return _pts
