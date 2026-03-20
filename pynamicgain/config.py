"""Configuration utilities for the PynamicGain package.

Handles reading, validating, and writing TOML setup files, directory
permission checks, and logging configuration. This module intentionally
avoids importing heavy scientific dependencies so that lightweight
tools (e.g. ``pydg_new_setup``) can use it without loading NumPy,
Matplotlib, etc.
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
import os
from typing import TYPE_CHECKING

import tomli

if TYPE_CHECKING:
    from pynamicgain._types import SetupConfig

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

        '# Author: Friedrich Schwarz <friedrich.schwarz@uni.goettingen.de>\n'
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


def load_config(cli_args: dict) -> "SetupConfig":
    """Load a setup TOML, merge CLI overrides, and return a frozen config.

    This is the preferred entry point for building a
    :class:`~pynamicgain._types.SetupConfig`. It replaces the dynamic
    attribute-setting logic that previously lived in ``PyDGBase.__init__``.

    Args:
        cli_args: Dictionary of command line arguments. Must contain at
            least ``'setup_dir'``. Other keys (e.g. ``'n_sweeps'``,
            ``'out_dir'``) override values from the TOML file.

    Returns:
        A frozen :class:`~pynamicgain._types.SetupConfig` instance.

    Raises:
        FileNotFoundError: If the setup directory or file is missing.
        ValueError: If the configuration is invalid.
    """
    from pynamicgain._types import SetupConfig  # deferred to avoid circular import

    setup_file, raw = read_setup_configs(cli_args['setup_dir'])

    # CLI args override TOML values (CLI wins)
    merged = dict(raw)
    for k, v in cli_args.items():
        if v is not None and k not in ('setup_dir',):
            merged[k] = v

    setup_dir = os.path.abspath(cli_args['setup_dir'])

    # Resolve default directories
    out_dir = merged.get('out_dir', '') or ''
    input_dir = merged.get('input_dir', '') or ''
    backup_dir = merged.get('backup_dir', '')
    analysis_dir = merged.get('analysis_dir', '')

    if not backup_dir:
        backup_dir = os.path.join(out_dir, 'backup') if out_dir else ''
    if not analysis_dir:
        analysis_dir = os.path.join(input_dir, 'analysis') if input_dir else ''

    # Create directories and check permissions
    for path, name in [
        (out_dir, 'output'),
        (input_dir, 'input'),
        (backup_dir, 'backup'),
        (analysis_dir, 'analysis'),
        (setup_dir, 'setup'),
    ]:
        if path:
            check_directory(path, name)

    # Build seed CSV path
    seed_csv = os.path.join(
        setup_dir,
        f'seed_list_setup_{merged["setup_id"]}.csv',
    )

    config = SetupConfig(
        version=merged['version'],
        master_seed=merged['master_seed'],
        n_seeds_per_setup=merged['n_seeds_per_setup'],
        current_seed_index=merged['current_seed_index'],
        setup_id=merged['setup_id'],
        setup_info=merged['setup_info'],
        config_file_creator=merged['config_file_creator'],
        creation_time=merged['creation_time'],
        stimulus_type=merged['stimulus_type'],
        n_sweeps=int(merged.get('n_sweeps', -1)),
        sampling_rate=int(merged.get('sampling_rate', -1)),
        duration=float(merged.get('duration', -1)),
        out_dir=out_dir,
        input_dir=input_dir,
        backup_dir=backup_dir,
        analysis_dir=analysis_dir,
        setup_dir=setup_dir,
        setup_file=setup_file,
        seed_csv=seed_csv,
        settings=merged.get('settings', {}),
        stimulus=merged.get('stimulus', {}),
        analysis=merged.get('analysis', {}),
        std=float(merged.get('std', 0.0)),
        corr_t=float(merged.get('corr_t', 0.0)),
    )

    logger.info("Loaded configuration for setup %d.", config.setup_id)
    return config


def check_directory(path: str, name: str) -> None:
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
