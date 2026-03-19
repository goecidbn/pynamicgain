# Changelog
All notable changes to this project will be documented in this file.

## [0.0.12] - 2026-03-19

### Changed
- **Module split**: The monolithic `__init__.py` (700+ lines) has been split into focused modules for better separation of concerns, testability, and debug-friendliness:
  - `config.py` — configuration I/O, validation, logging setup, directory checks. Lightweight (no scientific dependencies).
  - `base.py` — `PyDGBase` abstract base class.
  - `generator.py` — `PyDG` class with seed management and ABF generation.
  - `observer.py` — `PyDGAnalysis` class with observation mode and sweep analysis.
  - `__init__.py` — thin re-export layer (~50 lines). All existing imports (`from pynamicgain import PyDG`) continue to work unchanged.
- `_check_directory` renamed to `check_directory` (public API in `config.py`).
- `new_setup.py` imports `config_header` from `pynamicgain.config` directly, avoiding heavy dependency loading for the setup wizard.
- Default configuration version bumped to `0.0.12`.

## [0.0.11] - 2026-03-19

### Fixed
- **Seed management atomicity**: Seed state updates are now atomic. Seeds are generated in memory first, then persisted in a single batch after successful ABF file writing, preventing inconsistent state on crash.
- **Seed CSV is now the single source of truth**: On startup, `current_seed_index` is reconciled from the CSV file. The TOML value is kept for informational purposes only, eliminating TOML/CSV drift.
- **Config validation**: `read_setup_configs()` now validates all required keys and types with clear error messages instead of surfacing late `KeyError` exceptions.
- **Assertions replaced with explicit raises**: All `assert` statements in `new_setup.py` and `read_setup_configs()` replaced with `ValueError`/`RuntimeError` to ensure validation is not bypassed by `python -O`.
- **CLI type conversion errors**: Invalid CLI arguments now produce human-readable error messages instead of raw stack traces.
- **Division-by-zero in analysis**: MFR computation guarded against zero-duration recordings; CV computation guarded against zero-mean ISI.
- **Zero-length recording handling**: `minimal_spike_train_analysis` now returns `None` with a warning for empty traces instead of crashing.
- **Boolean comparison**: `if visualise == True` changed to `if visualise`.
- **Version mismatch assertion**: Version check in `new_setup.py` now raises `RuntimeError` and gracefully handles `__version__ == "unknown"` (uninstalled package).
- **Sampling rate mismatch**: Changed from `assert` to `raise ValueError` with informative message.

### Changed
- **Seed management architecture (Option D)**: `new_seed()` split into `_advance_seed()` (in-memory only) and `_log_seeds()` (batch CSV append + atomic TOML write). Eliminates O(n²) CSV rewrite per sweep.
- **Structured logging**: All `print()` calls in core modules replaced with Python `logging`. New `setup_logging()` function configures timestamped console output. Log level configurable via `settings.log_level` in the config file.
- **`PyDGBase` is now abstract**: Uses `ABC` to prevent direct instantiation.
- **`callable` type hint fixed**: `ask_set_input` parameter changed from bare `callable` to `Optional[Callable[[str], bool]]`.
- **Observation buffer configurable**: The hardcoded 180-second observation timeout buffer is now configurable via `settings.observation_buffer` in the config file.
- **Directory creation with permission checks**: `os.makedirs` calls now verify write permissions and raise `PermissionError` with clear messages.
- **Atomic file writes**: Setup TOML file is written via `tempfile` + `os.replace()` to prevent partial writes on crash.
- **Parameter validation in `exact_ou_process()`**: Duration, time step, correlation time, and fluctuation size are now validated with descriptive `ValueError` messages.
- **ABF file existence check**: `analyse_rec()` raises `FileNotFoundError` with a clear message if the ABF file is missing.
- **`analyse_file` CLI guard**: `analyse()` now checks that `--analyse_file` is provided when not in observation mode.

### Added
- `validate_setup_configs()` function for schema-level config validation.
- `_check_directory()` helper for directory creation with permission verification.
- `_reconcile_seed_index()` method to recover authoritative seed index from CSV on startup.
- `_persist_setup_file()` method for atomic TOML writes via temp file.
- `setup_logging()` public function for configuring package-level logging.
- `observation_buffer` setting in `[settings]` section of config (default: 180 seconds).
- `log_level` setting in `[settings]` section of config (default: `"INFO"`).

### Documentation
- Migrated CI deployment from `peaceiris/actions-gh-pages` to native GitHub Pages (`actions/upload-pages-artifact` + `actions/deploy-pages`).
- Added `-W --keep-going` to Sphinx build for warnings-as-errors.
- Added pip caching (`cache: 'pip'`) to CI workflow.
- Added separate `docs_check.yml` workflow for PR documentation checks.
- Removed `sphinx-apidoc` from build pipeline; kept `autosummary` as the sole API doc generator.
- Added `_autosummary/` and `_apidoc/` to `.gitignore`; removed committed auto-generated stubs.
- Created missing `docs/source/_static/custom.css`.
- Added intersphinx mappings for Python, NumPy, SciPy, Matplotlib, and pandas.
- Completed `deep_settings.md` with full parameter reference for all config sections.
- Documented new `observation_buffer` and `log_level` settings.

## [0.0.10] - 2026-03-19

### Fixed
- `read_setup_configs` return type hint now correctly declares `tuple[str, dict]`.
- `read_setup_configs` uses a single assertion requiring exactly one setup file.
- `ask_set_input` validation callable is now actually invoked (`_assert(_input)`) instead of only checking truthiness.
- Cross-platform path handling in `analyse_rec` (`os.path` instead of `rsplit('/')`).
- `analyse` type hint corrected from `Optional[float]` to `Optional[datetime]`.
- Zero and low spike count handling in `minimal_spike_train_analysis` (0, 1, or 2 spikes no longer crash; warnings are issued instead).
- Docstring parameter name `time_step` corrected to `dt` in `exact_ou_process`.
- Duplicate phrase removed from `config_header` docstring.
- Typo `pdyg_generate` corrected to `pydg_generate` in module docstring.
- Typo `aroubd` corrected to `around` in `get_cli_args` docstring.
- `--analyse_dir` option added to the docopt Usage line.
- RST link syntax fixed in `docs/source/index.rst` (missing trailing underscore).
- `SMPR.md` added to the Sphinx toctree.
- Typo in filename `matploltlib.mplstyle` corrected to `matplotlib.mplstyle`.

### Changed
- Repository moved from `fschwar4/pynamicgain` to `goecidbn/pynamicgain`; all URLs updated.
- Version is now read dynamically from package metadata (`importlib.metadata`) instead of being hardcoded in `__init__.py`.
- All docstrings converted to Google style for consistency with Sphinx Napoleon.
- Sphinx Napoleon configuration made explicit (`napoleon_google_docstring = True`, `napoleon_numpy_docstring = False`).
- Default configuration version bumped to `0.0.10`.

## [0.0.9] - 2024-06-01

### Added

Initial release of the package.
