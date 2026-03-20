"""Deterministic seed management for the PynamicGain package.

Provides :class:`SeedManager`, a standalone class that handles seed
generation, CSV persistence, and TOML reconciliation. Extracted from
the former ``PyDG`` class to follow the single-responsibility principle.
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


import csv
import logging
import os
import shutil
import tempfile

import pandas as pd
import tomli_w
from numpy.random import PCG64DXSM

from pynamicgain._types import SetupConfig
from pynamicgain.config import config_header

logger = logging.getLogger(__name__)


class SeedManager:
    """Manages deterministic seed generation and persistence.

    Seeds are drawn in memory via :meth:`draw` and batch-persisted via
    :meth:`commit`. The seed CSV is the single source of truth; the
    TOML ``current_seed_index`` is updated for informational purposes
    only.

    Args:
        config: The frozen setup configuration.

    Raises:
        FileNotFoundError: If the seed CSV file does not exist.

    Example::

        mgr = SeedManager(config)
        records = []
        for i in range(n_sweeps):
            idx, seed = mgr.draw()
            records.append({'seed index': idx, 'seed': seed, ...})
        mgr.commit(records)
    """

    def __init__(self, config: SetupConfig) -> None:
        self._config = config
        self._seed_csv = config.seed_csv
        self._setup_file = config.setup_file
        self._current_index = config.current_seed_index

        self._bg = PCG64DXSM(config.master_seed)
        self._bg.advance(
            config.current_seed_index
            + config.setup_id * config.n_seeds_per_setup
        )

        self.reconcile()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current_index(self) -> int:
        """The current seed index (in-memory value)."""
        return self._current_index

    def draw(self) -> tuple[int, int]:
        """Advance the seed index and draw a new seed from the RNG.

        This method only mutates in-memory state. Persistence is handled
        by :meth:`commit`.

        Returns:
            A tuple of ``(new_seed_index, new_seed)``.
        """
        self._current_index += 1
        new_seed = self._bg.random_raw()
        return self._current_index, int(new_seed)

    def commit(self, seed_records: list[dict]) -> None:
        """Append seed records to the CSV and persist the setup file.

        Uses append-only CSV writes and atomic TOML replacement to
        ensure consistency.

        Args:
            seed_records: List of dicts with keys ``'seed index'``,
                ``'seed'``, ``'sweep'``, ``'file'``, ``'backup'``.

        Raises:
            PermissionError: If the CSV file is not writable.
            OSError: If the CSV or TOML file cannot be written.
        """
        if not seed_records:
            return

        self._backup_csv()

        try:
            with open(self._seed_csv, 'a', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['seed index', 'seed', 'sweep', 'file', 'backup'],
                )
                for record in seed_records:
                    writer.writerow(record)
            logger.debug(
                "Appended %d seed record(s) to '%s'.",
                len(seed_records), self._seed_csv,
            )
        except PermissionError:
            raise PermissionError(
                f"Cannot write to seed CSV '{self._seed_csv}': permission denied."
            )
        except OSError as e:
            raise OSError(
                f"Failed to append to seed CSV '{self._seed_csv}': {e}. "
                f"Please check disk space and file system integrity."
            ) from e

        # Update TOML for informational purposes
        try:
            self._persist_setup_file()
        except OSError:
            logger.warning(
                "Seeds were logged to CSV but TOML update failed. "
                "The CSV remains the source of truth."
            )

    def reconcile(self) -> None:
        """Reconcile seed index from the CSV file (source of truth).

        If the CSV exists and contains entries, the maximum seed index
        is used as the authoritative value.

        Raises:
            FileNotFoundError: If the seed CSV file does not exist.
        """
        if not os.path.isfile(self._seed_csv):
            raise FileNotFoundError(
                f"Seed CSV file not found: '{self._seed_csv}'. "
                f"Please run 'pydg_new_setup' to create a new setup, "
                f"or check the setup directory."
            )

        try:
            df = pd.read_csv(self._seed_csv, index_col=False, header=0)
        except pd.errors.EmptyDataError:
            logger.debug("Seed CSV is empty (header only). Starting at index 0.")
            return
        except Exception as e:
            raise RuntimeError(
                f"Failed to read seed CSV '{self._seed_csv}': {e}. "
                f"The file may be corrupted. Please check the CSV manually "
                f"or contact the developer."
            ) from e

        if len(df) > 0 and 'seed index' in df.columns:
            csv_index = int(df['seed index'].max())
            if csv_index != self._current_index:
                logger.warning(
                    "Seed index mismatch: config has %d, CSV has %d. "
                    "Using CSV value (source of truth).",
                    self._current_index, csv_index,
                )
                self._current_index = csv_index
                # Re-position the RNG to match
                self._bg = PCG64DXSM(self._config.master_seed)
                self._bg.advance(
                    csv_index
                    + self._config.setup_id * self._config.n_seeds_per_setup
                )
                self._persist_setup_file()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def backup_csv(self) -> str:
        """Create a backup copy of the seed CSV.

        The backup is written to the same directory as the original with
        a ``.bak`` suffix.  When called from :meth:`commit` a failure is
        non-fatal (a warning is logged and the commit proceeds).  When
        called directly the exception propagates so the caller can
        handle it.

        Returns:
            The absolute path to the backup file.

        Raises:
            OSError: If the backup file cannot be written.

        .. versionadded:: 0.1.0
        """
        backup_path = self._seed_csv + '.bak'
        shutil.copy2(self._seed_csv, backup_path)
        logger.info("Backed up seed CSV to '%s'.", backup_path)
        return backup_path

    # keep the internal wrapper used by commit() ---
    def _backup_csv(self) -> None:
        """Best-effort backup called automatically by :meth:`commit`."""
        try:
            self.backup_csv()
        except OSError as e:
            logger.warning(
                "Could not back up seed CSV '%s': %s. "
                "Proceeding without backup.",
                self._seed_csv, e,
            )

    def _get_setup_dict(self) -> dict:
        """Return the setup configuration as a plain dict for TOML writing.

        Returns:
            Dictionary of public configuration keys with the current
            seed index updated.
        """
        import dataclasses
        d = dataclasses.asdict(self._config)
        d['current_seed_index'] = self._current_index
        # Remove internal path fields that are not part of the TOML
        for key in ('setup_dir', 'setup_file', 'seed_csv', 'std', 'corr_t'):
            d.pop(key, None)
        return d

    def _persist_setup_file(self) -> None:
        """Atomically write the setup TOML file via a temp file.

        Raises:
            OSError: If the file cannot be written.
        """
        setup_dir = os.path.dirname(self._setup_file)
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=setup_dir, suffix='.toml.tmp')
            setup_dict = self._get_setup_dict()
            with os.fdopen(fd, 'w') as f:
                f.write(config_header(setup_dict))
                f.write(tomli_w.dumps(setup_dict))
            os.replace(tmp_path, self._setup_file)
        except OSError as e:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise OSError(
                f"Failed to write setup file '{self._setup_file}': {e}. "
                f"Please check disk space and permissions."
            ) from e
