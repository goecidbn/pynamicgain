# Changelog
All notable changes to this project will be documented in this file.

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
