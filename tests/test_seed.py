"""Tests for pynamicgain.seed.SeedManager."""

import csv
import os

import pandas as pd
import pytest
import tomli
from numpy.random import PCG64DXSM, SeedSequence

from pynamicgain.seed import SeedManager


class TestSeedManagerInit:
    def test_init_with_valid_csv(self, sample_setup_config):
        mgr = SeedManager(sample_setup_config)
        assert mgr.current_index == 0

    def test_init_missing_csv(self, sample_setup_config, tmp_path):
        import dataclasses
        cfg = dataclasses.replace(
            sample_setup_config,
            seed_csv=str(tmp_path / "nonexistent.csv"),
        )
        with pytest.raises(FileNotFoundError, match="Seed CSV"):
            SeedManager(cfg)


class TestDraw:
    def test_returns_tuple(self, sample_setup_config):
        mgr = SeedManager(sample_setup_config)
        result = mgr.draw()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_increments_index(self, sample_setup_config):
        mgr = SeedManager(sample_setup_config)
        idx1, _ = mgr.draw()
        idx2, _ = mgr.draw()
        assert idx2 == idx1 + 1

    def test_deterministic(self, sample_setup_config):
        mgr1 = SeedManager(sample_setup_config)
        mgr2 = SeedManager(sample_setup_config)
        for _ in range(5):
            assert mgr1.draw() == mgr2.draw()

    def test_different_setup_ids(self, sample_setup_config, tmp_path):
        """Different setup_id values produce different seed sequences."""
        import dataclasses

        setup_dir2 = tmp_path / "setup2"
        setup_dir2.mkdir()
        seed_csv2 = setup_dir2 / "seed_list_setup_2.csv"
        with open(seed_csv2, "w", newline="") as f:
            csv.DictWriter(
                f,
                fieldnames=["seed index", "seed", "sweep", "file", "backup"],
            ).writeheader()

        cfg2 = dataclasses.replace(
            sample_setup_config,
            setup_id=2,
            seed_csv=str(seed_csv2),
            setup_dir=str(setup_dir2),
            setup_file=str(setup_dir2 / "setup_2.toml"),
        )
        mgr1 = SeedManager(sample_setup_config)
        mgr2 = SeedManager(cfg2)
        _, seed1 = mgr1.draw()
        _, seed2 = mgr2.draw()
        assert seed1 != seed2


class TestCommit:
    def test_appends_to_csv(self, sample_setup_config):
        mgr = SeedManager(sample_setup_config)
        records = []
        for i in range(3):
            idx, seed = mgr.draw()
            records.append({
                "seed index": idx,
                "seed": seed,
                "sweep": i,
                "file": "test.abf",
                "backup": "test_backup.abf",
            })
        mgr.commit(records)

        df = pd.read_csv(sample_setup_config.seed_csv)
        assert len(df) == 3
        assert list(df.columns) == ["seed index", "seed", "sweep", "file", "backup"]

    def test_empty_commit(self, sample_setup_config):
        mgr = SeedManager(sample_setup_config)
        mgr.commit([])  # should not raise or modify file
        df = pd.read_csv(sample_setup_config.seed_csv)
        assert len(df) == 0


class TestReconcile:
    def test_reconcile_from_csv(self, sample_setup_config):
        """When CSV has a higher index, reconcile adopts it."""
        mgr = SeedManager(sample_setup_config)

        # Draw and commit some seeds
        records = []
        for i in range(5):
            idx, seed = mgr.draw()
            records.append({
                "seed index": idx,
                "seed": seed,
                "sweep": i,
                "file": "f.abf",
                "backup": "b.abf",
            })
        mgr.commit(records)

        # Create a new manager — it should reconcile from CSV
        mgr2 = SeedManager(sample_setup_config)
        assert mgr2.current_index == 5

    def test_reconcile_continues_sequence(self, sample_setup_config):
        """After reconciliation, drawing continues the correct sequence."""
        mgr1 = SeedManager(sample_setup_config)

        # Draw 3 seeds, commit, then draw 2 more
        records = []
        for i in range(3):
            idx, seed = mgr1.draw()
            records.append({
                "seed index": idx,
                "seed": seed,
                "sweep": i,
                "file": "f.abf",
                "backup": "b.abf",
            })
        mgr1.commit(records)
        expected_4th = mgr1.draw()
        expected_5th = mgr1.draw()

        # New manager reconciles from CSV (index=3), should continue same sequence
        mgr2 = SeedManager(sample_setup_config)
        actual_4th = mgr2.draw()
        actual_5th = mgr2.draw()
        assert actual_4th == expected_4th
        assert actual_5th == expected_5th


class TestBackupCsv:
    def test_backup_csv_returns_path(self, sample_setup_config):
        """backup_csv() returns the backup path and creates the file."""
        mgr = SeedManager(sample_setup_config)
        bak_path = mgr.backup_csv()
        assert bak_path == sample_setup_config.seed_csv + ".bak"
        assert os.path.isfile(bak_path)

    def test_backup_csv_is_faithful_copy(self, sample_setup_config):
        """The .bak file is an exact copy of the original CSV."""
        mgr = SeedManager(sample_setup_config)
        # Add some data first
        idx, seed = mgr.draw()
        mgr.commit([{
            "seed index": idx, "seed": seed,
            "sweep": 0, "file": "f.abf", "backup": "b.abf",
        }])

        # Now take an explicit backup
        bak_path = mgr.backup_csv()
        with open(sample_setup_config.seed_csv) as orig, open(bak_path) as bak:
            assert orig.read() == bak.read()

    def test_commit_creates_backup(self, sample_setup_config):
        """commit() creates a .bak copy of the seed CSV."""
        mgr = SeedManager(sample_setup_config)
        idx, seed = mgr.draw()
        mgr.commit([{
            "seed index": idx, "seed": seed,
            "sweep": 0, "file": "f.abf", "backup": "b.abf",
        }])

        bak_path = sample_setup_config.seed_csv + ".bak"
        assert os.path.isfile(bak_path)

    def test_backup_contains_pre_commit_state(self, sample_setup_config):
        """The .bak file reflects the CSV state *before* the commit."""
        mgr = SeedManager(sample_setup_config)

        # First commit — CSV was empty (header only)
        idx, seed = mgr.draw()
        mgr.commit([{
            "seed index": idx, "seed": seed,
            "sweep": 0, "file": "f.abf", "backup": "b.abf",
        }])
        bak_path = sample_setup_config.seed_csv + ".bak"
        df_bak = pd.read_csv(bak_path)
        assert len(df_bak) == 0  # backup is the pre-commit state

        # Second commit — CSV now has 1 row
        idx2, seed2 = mgr.draw()
        mgr.commit([{
            "seed index": idx2, "seed": seed2,
            "sweep": 1, "file": "f.abf", "backup": "b.abf",
        }])
        df_bak2 = pd.read_csv(bak_path)
        assert len(df_bak2) == 1  # backup has the 1-row pre-commit state

    def test_empty_commit_no_backup(self, sample_setup_config):
        """An empty commit should not create a backup file."""
        mgr = SeedManager(sample_setup_config)
        mgr.commit([])
        bak_path = sample_setup_config.seed_csv + ".bak"
        assert not os.path.isfile(bak_path)


class TestPersistSetupFile:
    def test_produces_valid_toml(self, sample_setup_config):
        mgr = SeedManager(sample_setup_config)
        mgr.draw()
        mgr._persist_setup_file()

        with open(sample_setup_config.setup_file, "rb") as f:
            content = f.read()

        # The file has a header (comments) followed by TOML
        # Extract just the TOML portion by finding the first non-comment line
        lines = content.decode().split("\n")
        toml_lines = [
            line for line in lines
            if not line.startswith("#") and line.strip()
        ]
        # Parse the full file — tomli can handle comments
        with open(sample_setup_config.setup_file, "rb") as f:
            data = tomli.load(f)

        assert data["current_seed_index"] == 1
        assert data["setup_id"] == 1


class TestRNGArchitecture:
    """Verify the SeedSequence + PCG64DXSM architecture (v0.1.2)."""

    def test_bit_generator_class_attr(self):
        """SeedManager exposes the BitGenerator name."""
        assert SeedManager.BIT_GENERATOR == "PCG64DXSM"

    def test_uses_pcg64dxsm(self, sample_setup_config):
        """Internal BitGenerator is PCG64DXSM."""
        mgr = SeedManager(sample_setup_config)
        assert isinstance(mgr._bg, PCG64DXSM)

    def test_spawn_produces_independent_streams(self, sample_setup_config):
        """SeedSequence.spawn() child for setup_id=1 matches manual spawn."""
        mgr = SeedManager(sample_setup_config)
        # Manually construct the same child
        ss = SeedSequence(sample_setup_config.master_seed)
        child_ss = ss.spawn(1)[0]
        bg = PCG64DXSM(child_ss)
        # Both should produce the same first raw value
        expected = bg.random_raw()
        _, seed = mgr.draw()
        assert seed == int(expected)

    def test_create_bit_generator_static(self, sample_setup_config):
        """_create_bit_generator is deterministic."""
        bg1 = SeedManager._create_bit_generator(
            sample_setup_config.master_seed, 1, 0,
        )
        bg2 = SeedManager._create_bit_generator(
            sample_setup_config.master_seed, 1, 0,
        )
        assert bg1.random_raw() == bg2.random_raw()
