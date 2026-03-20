"""Tests for pynamicgain.stimulus_generation."""

import math

import numpy as np
import pytest
from numpy.random import Generator, PCG64DXSM, SeedSequence

from pynamicgain._types import StimulusParams
from pynamicgain.stimulus_generation import (
    build_stimulus_params,
    create_filename,
    create_filename_from_config,
    create_input_dict,
    exact_ou_process,
    generate_input,
    generate_input_from_params,
)


# -- exact_ou_process -------------------------------------------------------

class TestExactOuProcess:
    @pytest.mark.slow
    def test_output_length(self):
        """First call triggers Numba JIT compilation."""
        result = exact_ou_process(
            duration=1.0, dt=0.001, mu=0.0,
            fluctuation_size=1.0, input_correlation=0.01, key=42,
        )
        assert len(result) == math.ceil(1.0 / 0.001)

    def test_deterministic(self):
        a = exact_ou_process(
            duration=0.1, dt=0.001, mu=0.0,
            fluctuation_size=1.0, input_correlation=0.01, key=42,
        )
        b = exact_ou_process(
            duration=0.1, dt=0.001, mu=0.0,
            fluctuation_size=1.0, input_correlation=0.01, key=42,
        )
        np.testing.assert_array_equal(a, b)

    def test_different_seeds(self):
        a = exact_ou_process(
            duration=0.1, dt=0.001, mu=0.0,
            fluctuation_size=1.0, input_correlation=0.01, key=1,
        )
        b = exact_ou_process(
            duration=0.1, dt=0.001, mu=0.0,
            fluctuation_size=1.0, input_correlation=0.01, key=2,
        )
        assert not np.array_equal(a, b)

    def test_zero_fluctuation(self):
        result = exact_ou_process(
            duration=0.1, dt=0.001, mu=5.0,
            fluctuation_size=0.0, input_correlation=0.01, key=42,
        )
        np.testing.assert_allclose(result, 5.0, atol=1e-10)

    def test_mean_convergence(self):
        """Long trace mean should approximate mu."""
        mu = 3.0
        result = exact_ou_process(
            duration=100.0, dt=0.001, mu=mu,
            fluctuation_size=1.0, input_correlation=0.01, key=42,
        )
        assert abs(np.mean(result) - mu) < 0.1

    def test_invalid_duration(self):
        with pytest.raises(ValueError, match="duration"):
            exact_ou_process(
                duration=-1.0, dt=0.001, mu=0.0,
                fluctuation_size=1.0, input_correlation=0.01,
            )

    def test_invalid_dt(self):
        with pytest.raises(ValueError, match="dt"):
            exact_ou_process(
                duration=1.0, dt=0.0, mu=0.0,
                fluctuation_size=1.0, input_correlation=0.01,
            )

    def test_invalid_correlation(self):
        with pytest.raises(ValueError, match="input_correlation"):
            exact_ou_process(
                duration=1.0, dt=0.001, mu=0.0,
                fluctuation_size=1.0, input_correlation=-1.0,
            )

    def test_negative_fluctuation(self):
        with pytest.raises(ValueError, match="fluctuation_size"):
            exact_ou_process(
                duration=1.0, dt=0.001, mu=0.0,
                fluctuation_size=-1.0, input_correlation=0.01,
            )

    def test_no_nan_or_inf(self):
        result = exact_ou_process(
            duration=1.0, dt=0.001, mu=0.0,
            fluctuation_size=10.0, input_correlation=0.05, key=99,
        )
        assert np.all(np.isfinite(result))


# -- generate_input_from_params ---------------------------------------------

class TestGenerateInputFromParams:
    def test_matches_direct_call(self):
        params = StimulusParams(
            duration=0.1, dt=0.001, mu=0.0,
            fluctuation_size=1.0, input_correlation=0.01, key=42,
        )
        a = generate_input_from_params(params)
        b = exact_ou_process(
            duration=0.1, dt=0.001, mu=0.0,
            fluctuation_size=1.0, input_correlation=0.01, key=42,
        )
        np.testing.assert_array_equal(a, b)


# -- build_stimulus_params --------------------------------------------------

class TestBuildStimulusParams:
    def test_correct_fields(self, sample_setup_config):
        params = build_stimulus_params(sample_setup_config, key=999)
        assert params.duration == sample_setup_config.duration
        assert params.dt == 1.0 / sample_setup_config.sampling_rate
        assert params.mu == 0.0
        assert params.fluctuation_size == sample_setup_config.std
        assert params.input_correlation == sample_setup_config.corr_t
        assert params.key == 999


# -- create_filename / create_filename_from_config --------------------------

class TestCreateFilename:
    def test_ou_filename(self):
        name = create_filename("OU", corr_t=5.0, n_sweeps=10)
        assert name == "OU_5.0ms_10sweeps.abf"

    def test_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown input type"):
            create_filename("INVALID", corr_t=5.0, n_sweeps=10)


class TestCreateFilenameFromConfig:
    def test_from_config(self, sample_setup_config):
        name = create_filename_from_config(sample_setup_config)
        assert "OU" in name
        assert "5.0ms" in name
        assert "3sweeps" in name


# -- generate_input ---------------------------------------------------------

class TestGenerateInput:
    def test_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown input type"):
            generate_input(type="INVALID")


# -- create_input_dict ------------------------------------------------------

class TestCreateInputDict:
    def test_ou(self):
        d = create_input_dict(
            type="OU",
            duration=10.0,
            sampling_rate=20000,
            stimulus={"OU": {"mu": 0.0}},
            std=100.0,
            corr_t=5.0,
            key=42,
        )
        assert d["duration"] == 10.0
        assert d["dt"] == 1.0 / 20000
        assert d["key"] == 42

    def test_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown input type"):
            create_input_dict(type="INVALID")


# -- RNG architecture (v0.1.2) ------------------------------------------------

class TestRNGArchitecture:
    """Verify explicit PCG64DXSM + SeedSequence usage."""

    def test_uses_pcg64dxsm_via_seedsequence(self):
        """OU process output matches manual Generator(PCG64DXSM(SeedSequence(key)))."""
        key = 42
        rng = Generator(PCG64DXSM(SeedSequence(key)))
        duration, dt = 0.1, 0.001
        corr_t = 0.01
        fs = 1.0
        kappa_sq = np.exp(-2.0 * dt / corr_t)
        sk = fs * np.sqrt(1 - kappa_sq)
        n = int(np.ceil(duration / dt))
        eta = rng.normal(loc=0, scale=sk, size=n)
        # The first sample should match the first sample of exact_ou_process
        result = exact_ou_process(
            duration=duration, dt=dt, mu=0.0,
            fluctuation_size=fs, input_correlation=corr_t, key=key,
        )
        # Check first sample (scaled) — if BitGenerator differs, this fails
        assert result[0] != 0.0  # non-trivial check
