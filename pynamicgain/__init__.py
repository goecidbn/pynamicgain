"""PynamicGain: Dynamic Gain inputs for distributed patch clamp setups.

This package generates Ornstein-Uhlenbeck process stimuli for
electrophysiology experiments and provides on-the-fly spike train
analysis of the resulting recordings.

All public classes and functions are re-exported here so that existing
imports (e.g. ``from pynamicgain import PyDG``) continue to work.
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


from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pynamicgain")
except PackageNotFoundError:
    __version__ = "unknown"

# Configuration and setup
from pynamicgain.config import (
    setup_logging,
    config_header,
    read_setup_configs,
    validate_setup_configs,
    check_directory,
    load_config,
)

# Typed data containers (new in v0.1.0)
from pynamicgain._types import (
    SetupConfig,
    StimulusParams,
    AnalysisParams,
    VisualisationParams,
    SpikeMetrics,
)

# Seed management (new in v0.1.0)
from pynamicgain.seed import SeedManager

# Analysis (new split API in v0.1.0)
from pynamicgain.analysis import compute_spike_metrics, plot_sweep_analysis

# Core classes (backwards-compatible)
from pynamicgain.base import PyDGBase
from pynamicgain.generator import PyDG
from pynamicgain.observer import PyDGAnalysis

__all__ = [
    "__version__",
    # Config
    "setup_logging",
    "config_header",
    "read_setup_configs",
    "validate_setup_configs",
    "check_directory",
    "load_config",
    # Types
    "SetupConfig",
    "StimulusParams",
    "AnalysisParams",
    "VisualisationParams",
    "SpikeMetrics",
    # Seed management
    "SeedManager",
    # Analysis
    "compute_spike_metrics",
    "plot_sweep_analysis",
    # Core classes
    "PyDGBase",
    "PyDG",
    "PyDGAnalysis",
]
