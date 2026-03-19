"""Module to generate the input for the dynamic gain calculations.

Currently the input is generated as an OU process with a given correlation time and standard deviation.

In the future, this can be extended to more complex input signals.
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


import numpy as np
from numpy.typing import NDArray
from numba import njit


def generate_input(type: str = 'OU', **kwargs) -> NDArray[np.float64]:
    """Wrapper to generate input for the dynamic gain calculation.
    
    This function generates the input for the dynamic gain calculation.
    Currently, only the Ornstein-Uhlenbeck process is implemented.
    
    Args:
        type (str, optional): The type of input to generate. Defaults to 'OU'.
    
    Returns:
        NDArray[np.float64]: The generated input signal.
    """
    input_kwargs = create_input_dict(type, **kwargs)
    
    if type == 'OU':
        return exact_ou_process(**input_kwargs)
    else:
        raise ValueError(f"Unknown input type: {type}")
    
    

def create_input_dict(type: str = 'OU', **kwargs):
    """Creating/Parsing the relevant parameters for the input generation."""
    if type == 'OU':
        _kwargs = {
            "duration": kwargs['duration'],
            "dt": 1.0/kwargs['sampling_rate'],
            "mu": kwargs['stimulus']['OU']['mu'],
            "fluctuation_size": kwargs['std'],
            "input_correlation": kwargs['corr_t'],
            "key": kwargs['key'],
        }
    else:
        raise ValueError(f"Unknown input type: {type}")

    return _kwargs


def create_filename(type: str = 'OU', **kwargs):
    """Creating the filename for the input file.
    
    This depends on the input type and the parameters used for the input
    generation.
    """
    if type == 'OU':
        _filename = f"OU_{kwargs['corr_t']}ms_{kwargs['n_sweeps']}sweeps.abf"
    else:
        raise ValueError(f"Unknown input type: {type}")

    return _filename


@njit()
def inner_exact(eta, mu, _kappa):
    """
    Inner function calculating the exact OU-process solution step by step.
    Using numba JIT for speedup.
    """
    for i in range(1, len(eta)):
        eta[i] += eta[i-1] * _kappa
    return eta + mu


def exact_ou_process(
    duration: int, 
    dt: float, 
    mu: float,
    fluctuation_size: float,
    input_correlation: float,
    key: int = 10) -> NDArray[np.float64]:
    """Generate an Ornstein-Uhlenbeck process.
    
    Numba-based implementation generating an Ornstein-Uhlenbeck process.
    Using JIT power for speedup.
    
    Parameters:
        duration (int): Duration of the simulation in seconds.
        dt (float): Duration of one time step of the simulation.
        mu (float): Average input strength.
        fluctuation_size (float): The size of the process' fluctuation.
        input_correlation (float): The correlation time of the input in
            seconds.
            
    Returns:
        NDArray[np.double]: Simulation trace of the Ornstein-Uhlenbeck
            Process, given the certain arguments.
            shape=(1,trace_length)
            dtype= np.double
            
    Other Parameters:
        kappa (float): Decay Parameter, implementing the correlation
            between the time steps.
        kappa_sq (float): Square root of decay Parameter (`kappa`). Used
            for calculating the next step.
        sk (float): Product of `fluctuation_size` and `kappa_sq`. Since
            this is static. This variable is called within the loop of
            the trace calculation.
        eta (NDArray[np.double]): Vector of (pre-calculated) random numbers,
            used to calculate the next time step. The values are gene- rated
            before the calculation loop and drawn from a Standard Gaussian
            distribution.
        trace_length (int): Number of elements within the trace.
            Calculated by dividing the duration by the time step length.

    Note:
        The first value is simply derived by multiplying the scale para-
        meter (`fluctuation_size`) with a randomly drawn number.

        Every following time step is calculated by the multiplying the
        time step before with the decay parameter (`kappa`) and adding a
        new randomly drawn number multiplied by the square root of the
        (`kappa_sq`) and the scaling parameter (`fluctuation_size`).

        Lastly the average input strength (`mu`) is added in one step.
        This step is equivalent to adding it in every step, since
        Ornstein-Uhlenbeck processes evolve with fixed mean.

       All functions in this file, use one numpy random number generator
       (RNG_OU). The RNG_OU is instantiated once, the file or one
       function is called. This has the advantage, that repeated runs
       are reproducible. But, please keep in mind, that multiple calls
       of the single trace functions, will always give the same trace.
       Please call the `ornstein_uhlenbeck_multiple()` function for
       multiple (and different) traces.

    References:
        The calculation is based on Gillespie 1996 (Phys Rev E).
        Following parameters correspond to the author's original notion:

        |    fluctuation_size : sigma
        |    input_correlation : tauI

        The variables calculated within the function are also based on
        this paper: kappa, kappa_sq and eta.
        Eta is drawn from a Standard Gaussian distribution.
    
    """
    RNG_ = np.random.default_rng(seed=key)
    
    _kappa_sq = np.exp(-2.0 * dt / input_correlation)
    _sk = fluctuation_size * np.sqrt(1 - _kappa_sq)
    
    eta = RNG_.normal(loc=0, scale=_sk, size=int(np.ceil(duration/dt)))
    eta[0] /= np.sqrt(1 - _kappa_sq)

    return inner_exact(eta, mu, np.exp(-dt / input_correlation))
