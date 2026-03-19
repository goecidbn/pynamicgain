"""Main module for the PynamicGain package.

The following docopt code is only used for pydg_generate, pydg_analyse,
pydg_generate_analyse. Please note that pynamicgain is only a pattern
placeholder. The actual entry point is defined via setuptools. It is not used
for pydg_new_setup and pydg_help as these functions do not require command line
arguments.

Usage:
    pynamicgain [<std>] [<corr_t>] [--setup_dir=<sudir>] [--n_sweeps=<ns>] [--duration=<dt>] [--out_dir=<od>] [--input_dir=<pd>] [--sampling_rate=<sr>] [--visualise=<v>] [--analyse_file=<af>] [--backup_dir=<bd>] [--analyse_dir=<ad>]

Options:
    -h --help     Show this screen.

Arguments:
    <std>  Standard deviation of the noise.
    <corr_t>  Correlation time of the noise.
    --setup_dir=<sudir>  Path to the configuration directory. [default: .]
    --n_sweeps=<ns>  Number of sweeps to create.
    --duration=<dt>  Duration of the recordings.
    --out_dir=<od>  Output directory for the ABF file. [default: .]
    --input_dir=<pd>  Path to the pClamp directory. [default: .]
    --sampling_rate=<sr>  Sampling rate of the recordings.
    --visualise=<v>  Whether to visualise the results.
    --analyse_file=<af>  Path to the file to analyse.
    --backup_dir=<bd>  Path to the backup directory. [default: .]
    --analyse_dir=<ad>  Path to the directory where to save the analysis results. [default: .]

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
import sys
from datetime import datetime as dt
from typing import Optional

import docopt

from pynamicgain import PyDG, PyDGAnalysis, setup_logging

logger = logging.getLogger(__name__)


def _parse_cli_float(value: str, name: str) -> float:
    """Convert a CLI string argument to float with a clear error message.

    Args:
        value: The raw string value from the CLI.
        name: The argument name for the error message.

    Returns:
        The parsed float value.

    Raises:
        SystemExit: If the value cannot be converted to float.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        print(f"Error: '--{name}' must be a number, got '{value}'.", file=sys.stderr)
        sys.exit(1)


def _parse_cli_int(value: str, name: str) -> int:
    """Convert a CLI string argument to int with a clear error message.

    Args:
        value: The raw string value from the CLI.
        name: The argument name for the error message.

    Returns:
        The parsed integer value.

    Raises:
        SystemExit: If the value cannot be converted to int.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        print(f"Error: '--{name}' must be an integer, got '{value}'.", file=sys.stderr)
        sys.exit(1)


def get_cli_args() -> dict:
    """Parse and normalise command line arguments via docopt.

    Strips docopt key prefixes (``--``, ``<>``) and converts values to
    their expected Python types. Directory paths set to ``'.'`` are
    resolved to the current working directory.

    Returns:
        Normalised keyword arguments ready for class instantiation.
    """
    kwargs = docopt.docopt(__doc__)  # read

    # modify kwargs (remove -- and </> from keys)
    kwargs = {
        k.replace('--', '', 1).replace('<', '').replace('>', ''): v
        for k, v in kwargs.items() if v is not None
    }

    # set absolute paths for cwd
    for k, v in kwargs.items():
        if 'dir' in k and v == '.':  # current directory
            kwargs[k] = os.getcwd()

    # convert to correct types with informative error messages
    if 'std' in kwargs:
        kwargs['std'] = _parse_cli_float(kwargs['std'], 'std')
    if 'corr_t' in kwargs:
        kwargs['corr_t'] = _parse_cli_float(kwargs['corr_t'], 'corr_t')
    if 'n_sweeps' in kwargs:
        kwargs['n_sweeps'] = _parse_cli_int(kwargs['n_sweeps'], 'n_sweeps')
    if 'duration' in kwargs:
        kwargs['duration'] = _parse_cli_float(kwargs['duration'], 'duration')
    if 'sampling_rate' in kwargs:
        kwargs['sampling_rate'] = _parse_cli_int(kwargs['sampling_rate'], 'sampling_rate')
    if 'refractory_period' in kwargs:
        kwargs['refractory_period'] = _parse_cli_float(kwargs['refractory_period'], 'refractory_period')
    if 'min_spike_height' in kwargs:
        kwargs['min_spike_height'] = _parse_cli_float(kwargs['min_spike_height'], 'min_spike_height')
    if 'visualise' in kwargs:
        kwargs['visualise'] = kwargs['visualise'].lower() == 'true'

    kwargs.pop('help', None)  # not needed, only for docopt

    return kwargs


def generate(only_generate: bool = True) -> Optional[dt]:
    """Generate input signals and write them to ABF files.

    Args:
        only_generate: If True, print a goodbye message and return None.
            If False, return the generation timestamp for downstream
            analysis scheduling.

    Returns:
        The generation timestamp when ``only_generate`` is False,
        otherwise None.
    """
    setup_logging()
    logger.info("Generating input signals...")
    cl_args = get_cli_args()
    myPG = PyDG(cl_args)
    _timestamp = myPG.create_input_abf()

    logger.info(
        "Generation complete. ABF files saved to output and backup directories."
    )

    if only_generate:
        print('Thank you for using PynamicGain!\n')
        return None
    else:
        return _timestamp


def analyse(start_time: Optional[dt] = None) -> None:
    """Analyse patch clamp recordings.

    When ``start_time`` is provided, enters observation mode and monitors
    the input directory for new ABF files. Otherwise, analyses the file
    specified via the ``--analyse_file`` CLI argument.

    Args:
        start_time: If provided, the timestamp from which to observe
            the input directory for new recordings. Defaults to None.
    """
    setup_logging()
    cl_args = get_cli_args()
    myPDGA = PyDGAnalysis(cl_args, start_time)
    if start_time:
        _left = myPDGA.observe()
    else:
        if 'analyse_file' not in cl_args:
            print("Error: --analyse_file is required when not in observation mode.", file=sys.stderr)
            sys.exit(1)
        _left = myPDGA.analyse_rec(cl_args['analyse_file'])

    if _left == 0:
        logger.info("All sweeps analysed.")
    else:
        logger.warning("Time limit reached. %d sweep(s) left to analyse.", _left)

    print('\nThank you for using PynamicGain!\n')


def generate_analyse() -> None:
    """Generate input signals and immediately analyse the recordings.

    Combines :func:`generate` and :func:`analyse` into a single workflow.
    """
    _starttime = generate(only_generate=False)
    analyse(_starttime)


def help() -> None:
    """Print available PynamicGain CLI commands and contact information."""
    print(
        '\n'
        'PynamicGain: Python-based Dynamic Gain inputs for your patch clamp setup.\n'
        '\n'
        'Commands:\n'
        '  pydg_new_setup          Generate a new setup configuration file.\n'
        '  pydg_generate           Generate input signals.\n'
        '  pydg_generate_analyse   Generate input and analyse new recordings.\n'
        '  pydg_analyse            Analyse a specific recording.\n'
        '  pydg_help               Show this help message.\n'
        '\n'
        'Please report bugs to <friedrichschwarz@unigoettingen.de>.\n'
        'PynamicGain homepage: <https://github.com/goecidbn/pynamicgain>.\n\n'
    )


if __name__ == '__main__':
    pass
