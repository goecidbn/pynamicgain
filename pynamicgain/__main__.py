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


import os
from datetime import datetime as dt
from typing import Optional

import docopt

from pynamicgain import PyDG, PyDGAnalysis


def get_cli_args():
    """Wrapper around docopt to get the CLI arguments."""
    kwargs = docopt.docopt(__doc__)  # read
    
    # modify kwargs (remove -- and </> from keys)
    kwargs ={
        k.replace('--', '', 1).replace('<', '').replace('>', ''): v 
        for k, v in kwargs.items() if v is not None
        }
    
    # set absolute paths for cwd
    for k, v in kwargs.items():
        if 'dir' in k and v == '.':  # current directory
            kwargs[k] = os.getcwd()
    
    # convert to correct types
    if 'std' in kwargs:
        kwargs['std'] = float(kwargs['std'])
    if 'corr_t' in kwargs:
        kwargs['corr_t'] = float(kwargs['corr_t'])
    if 'n_sweeps' in kwargs:
        kwargs['n_sweeps'] = int(kwargs['n_sweeps'])
    if 'duration' in kwargs:
        kwargs['duration'] = float(kwargs['duration'])
    if 'sampling_rate' in kwargs:
        kwargs['sampling_rate'] = int(kwargs['sampling_rate'])
    if 'refractory_period' in kwargs:
        kwargs['refractory_period'] = float(kwargs['refractory_period'])
    if 'min_spike_height' in kwargs:
        kwargs['min_spike_height'] = float(kwargs['min_spike_height'])
    if 'visualise' in kwargs:
        kwargs['visualise'] = kwargs['visualise'].lower() == 'true'
        
    kwargs.pop('help', None)  # not needed, only for docopt
    
    return kwargs
    
    
def generate(only_generate: bool = True):
    print('\nGenerating input signals...\n')
    cl_args = get_cli_args()
    myPG = PyDG(cl_args)
    _timestamp = myPG.create_input_abf()
    
    print(
        '\nThe generation of input signals is now complete.\n'
        'The ABF files are saved in the output directory and the backups in the backup directory.\n'
    )
    
    if only_generate:
        print('Thank you for using PynamicGain!\n')
        return None
    else:
        return _timestamp


def analyse(start_time: Optional[dt] = None):
    cl_args = get_cli_args()
    myPDGA = PyDGAnalysis(cl_args, start_time)
    if start_time:
        _left = myPDGA.observe()
    else:
        _left = myPDGA.analyse_rec(cl_args['analyse_file'])
        
    if _left == 0:
        print('All Sweeps analysed.')
    else:
        print(f'Time limit reached. {_left} Sweeps left to analyse.')

    print('\nThank you for using PynamicGain!\n')
    

def generate_analyse():
    _starttime = generate(only_generate=False)
    analyse(_starttime)


def help():
    """
    Prints a help message detailing the commands available in the PynamicGain program.

    The help message includes a brief description of the program, a list of commands,
    contact information for reporting bugs, and the homepage of the program.

    Args:
        None

    Returns:
        None
    """
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
