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
    """Generate an input signal for the dynamic gain calculation.

    Currently only the Ornstein-Uhlenbeck (OU) process is implemented.

    Args:
        type: The type of input to generate. Defaults to ``'OU'``.
        **kwargs: Forwarded to :func:`create_input_dict` for parameter
            extraction.

    Returns:
        The generated input signal as a 1-D array.

    Raises:
        ValueError: If ``type`` is not a recognised input type.
    """
    input_kwargs = create_input_dict(type, **kwargs)
    
    if type == 'OU':
        return exact_ou_process(**input_kwargs)
    else:
        raise ValueError(f"Unknown input type: {type}")
    
    

def create_input_dict(type: str = 'OU', **kwargs) -> dict:
    """Extract and normalise parameters for input generation.

    Args:
        type: The type of input to generate. Defaults to ``'OU'``.
        **kwargs: Must contain ``duration``, ``sampling_rate``,
            ``stimulus``, ``std``, ``corr_t``, and ``key``.

    Returns:
        Dictionary of keyword arguments for the generator function.

    Raises:
        ValueError: If ``type`` is not a recognised input type.
    """
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


def create_filename(type: str = 'OU', **kwargs) -> str:
    """Build a standardised filename for the input ABF file.

    The filename encodes the input type and key parameters.

    Args:
        type: The type of input to generate. Defaults to ``'OU'``.
        **kwargs: Must contain ``corr_t`` and ``n_sweeps``.

    Returns:
        The generated filename string (e.g. ``OU_5ms_10sweeps.abf``).

    Raises:
        ValueError: If ``type`` is not a recognised input type.
    """
    if type == 'OU':
        _filename = f"OU_{kwargs['corr_t']}ms_{kwargs['n_sweeps']}sweeps.abf"
    else:
        raise ValueError(f"Unknown input type: {type}")

    return _filename


@njit()
def inner_exact(eta, mu, _kappa):
    """Compute the exact OU-process solution step-by-step (Numba JIT).

    Applies the recursive relation in-place on ``eta``, then adds the
    mean ``mu``.

    Args:
        eta: Pre-allocated noise vector (modified in-place).
        mu: Mean of the OU process.
        _kappa: Decay parameter ``exp(-dt / tau)``.

    Returns:
        The completed OU trace (``eta + mu``, same array).
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

    Numba-accelerated implementation based on Gillespie 1996 (Phys Rev E).

    Args:
        duration: Duration of the simulation in seconds.
        dt: Duration of one time step of the simulation in seconds.
        mu: Average input strength (mean of the OU process).
        fluctuation_size: Standard deviation of the process
            (corresponds to *sigma* in Gillespie 1996).
        input_correlation: Correlation time of the input in seconds
            (corresponds to *tauI* in Gillespie 1996).
        key: Seed for the random number generator. Defaults to 10.

    Returns:
        Simulation trace of the Ornstein-Uhlenbeck process with shape
        ``(trace_length,)`` and dtype ``np.double``.

    Note:
        The first value is scaled to the stationary standard deviation.
        Each subsequent step applies the decay parameter *kappa* and
        adds scaled Gaussian noise. The mean *mu* is added in a single
        vectorised step at the end (valid because OU processes evolve
        with a fixed mean).

        Internally computed variables (following Gillespie 1996):

        - **kappa**: Decay parameter ``exp(-dt / input_correlation)``.
        - **kappa_sq**: ``exp(-2 * dt / input_correlation)``.
        - **sk**: ``fluctuation_size * sqrt(1 - kappa_sq)``.
        - **eta**: Pre-drawn Gaussian noise vector.

    References:
        Gillespie, D. T. (1996). Exact numerical simulation of the
        Ornstein-Uhlenbeck process and its integral. *Physical Review E*,
        54(2), 2084.
    """
    RNG_ = np.random.default_rng(seed=key)
    
    _kappa_sq = np.exp(-2.0 * dt / input_correlation)
    _sk = fluctuation_size * np.sqrt(1 - _kappa_sq)
    
    eta = RNG_.normal(loc=0, scale=_sk, size=int(np.ceil(duration/dt)))
    eta[0] /= np.sqrt(1 - _kappa_sq)

    return inner_exact(eta, mu, np.exp(-dt / input_correlation))
