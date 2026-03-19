"""Module to generate a new setup configuration file.

Please run this script to generate a new setup configuration file.
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
from importlib.resources import open_binary

import pandas as pd
import tomli
import tomli_w

from pynamicgain import config_header, __version__


def ask_set_input(question: str, prompt: str, _assert: callable = None):
    """Prompt the user with a yes/no question and optionally collect input.

    If the user answers *yes*, they are asked for a value that is
    validated with ``_assert``. Up to 5 invalid attempts are allowed
    before raising an error.

    Args:
        question: The yes/no question to display.
        prompt: The follow-up prompt for the actual value.
        _assert: Optional validation callable. Receives the stripped
            user input and should return True if valid.

    Returns:
        The validated user input string, or None if the user answered
        *no*.

    Raises:
        RuntimeError: If the maximum number of invalid attempts is
            reached.
    """
    c_ = 0
    _input = None
    while True and c_ < 5:
        _ifp = input(f'\n{question} (y/n): ')
        if _ifp.lower() not in ['y', 'n']:
            print("Invalid input. Please enter 'y' or 'n'.")
            c_ += 1
            continue
        if _ifp.lower() == 'y':
            while c_ < 5:
                _input = input(f'\t{prompt}: ')
                _input = _input.strip()
                if _assert and _assert(_input):
                    break
                else:
                    print("Invalid input.")
                    c_ += 1
        break
    
    if c_ == 5:
        raise RuntimeError("Too many invalid inputs.")
    
    return _input if _input else None
        

def initiate_new_setup() -> None:
    """Interactively create a new setup configuration file for DG on pClamp.

    Prompts the user for:

    - **setup id** -- positive integer (coordinate with your team first).
    - **setup description** -- short free-text description.
    - **setup creator** -- your name.
    - **output path** -- where ``.abf`` files will be saved (optional).
    - **input path** -- where patch clamp recordings are stored (optional).
    - **sampling rate**, **n_sweeps**, **duration** -- recording parameters
      (optional, stored as defaults).
    - **save path** -- where the configuration file will be written.

    The generated TOML configuration file and a companion seed-list CSV
    are written to the specified save path.

    Raises:
        AssertionError: If the setup id, description, creator, or save
            path are invalid.
        FileExistsError: If a configuration file for the given setup id
            already exists at the save path.
    """
    print('\nWelcome to the setup configuration file generator.')
    
    # get setup id and description from user
    setup_id = int(input("Please enter setup id: "))  # user input
    assert 0 < setup_id <= 20, "setup id must be between 1 and 20"  # might be changed in the future

    setup_info = input("Please enter short setup description: ")  # user input
    setup_info = setup_info.strip()
    assert len(setup_info) > 0, "setup description must not be empty"
    
    setup_creator = input('Please enter your name: ')  # user input
    setup_creator = setup_creator.strip()
    assert len(setup_creator) > 0, "setup creator must not be empty"
    
    output_dir = ask_set_input(
        'Do you want to set an output path?', 
        'Please enter the output path', 
        lambda x: len(x) > 0
    )

    input_dir = ask_set_input(
        'Do you want to set an input path (for the patch clamp recordings)?', 
        'Please enter the input path',
        lambda x: len(x) > 0
    )
        
    save_path = input('\nPlease enter the path where the setup configuration file will be saved: ')  # user input
    save_path = save_path.strip()
    assert len(save_path) > 0, "save path must not be empty"
    save_path = os.path.abspath(save_path)
    
    print('\nSome settings may change infrequently for a given setup '
          '(e.g. sampling rate, recording time or number of sweeps).')
    while True:
        _sas = input('Do you want to store additional default configurations in the setup file? (y/n): ')
        if _sas.lower() in ['y', 'n']:
            break
        print("Invalid input. Please enter 'y' or 'n'.")
        
    if _sas == 'y':
        sampling_rate = ask_set_input(
            'Do you want to set the sampling rate?',
            'Please enter the sampling rate [Hz]', 
            lambda x: x.isdigit() and int(x) > 0
        )
        
        n_sweeps = ask_set_input(
            'Do you want to set the number of sweeps?',
            'Please enter the number of sweeps',
            lambda x: x.isdigit() and int(x) > 0
        )
        
        duration = ask_set_input(
            'Do you want to set the duration of the sweeps?',
            'Please enter the duration of the sweeps [s]',
            lambda x: x.isdigit() and int(x) > 0
        )
        
        backup_dir = ask_set_input(
            'Do you want to set a backup directory (if not, it will be a subdirectory of the output directory)?',
            'Please enter the backup directory',
            lambda x: len(x) > 0
        )
        
        analysis_dir = ask_set_input(
            'Do you want to set an analysis directory?',
            'Please enter the analysis directory',
            lambda x: len(x) > 0
        )
    else:  # create empty variables so they are at least in the namespace
        sampling_rate = n_sweeps = duration = backup_dir = analysis_dir = None

    creation_time = time.strftime("%d.%m.%Y %H:%M:%S")  # current time

    with open_binary("pynamicgain.default_configs", "default_configs.toml") as config_file:
        setup = tomli.load(config_file)
        
    assert setup['version'] == __version__, "Code and Default Configurations Versions do not match!"
        
    # update setup configuration file
    setup['setup_id'] = setup_id
    setup['setup_info'] = setup_info
    setup['config_file_creator'] = setup_creator
    setup['creation_time'] = creation_time
    setup['current_seed_index'] = 0
    setup['out_dir'] = output_dir if output_dir else ''
    setup['input_dir'] = input_dir if input_dir else ''
    setup['sampling_rate'] = int(sampling_rate) if sampling_rate else -1
    setup['n_sweeps'] = int(n_sweeps) if n_sweeps else -1
    setup['duration'] = float(duration) if duration else -1
    setup['backup_dir'] = backup_dir if backup_dir else ''
    setup['analysis_dir'] = analysis_dir if analysis_dir else setup['input_dir']
    
    # write setup configuration file
    os.makedirs(os.path.abspath(save_path), exist_ok=True)
    save_config_path = os.path.join(save_path, f'setup_{setup_id}.toml')
    if os.path.exists(save_config_path):
        raise FileExistsError(f"\n\nSetup configuration file for setup {setup_id} already exists.")
    with open(save_config_path, 'w') as f:
        f.write(config_header(setup))  # config file header
        f.write(tomli_w.dumps(setup))  # config file content
        
    print(f'\nSuccessfully created setup configuration file for setup {setup_id}.')
    
    # create seed backup file
    df_ = pd.DataFrame(columns=['seed index', 'seed', 'sweep', 'file', 'backup'])
    df_.to_csv(os.path.join(save_path, f'seed_list_setup_{setup_id}.csv'), index=False)

    print(f'Successfully created seed backup file for setup {setup_id}.')
    
    print('Initialization done. If you want to change the setup configuration file, please edit the file manually.\n')
