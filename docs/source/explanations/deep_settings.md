# Advanced Settings

The setup configuration file (TOML format) controls every aspect of stimulus
generation and online analysis. This page documents each section and parameter
so you can fine-tune the behaviour beyond the defaults created by
`pydg_new_setup`.

## File Structure Overview

A setup configuration file has four main sections:

| Section | Purpose |
|---------|---------|
| *Top-level keys* | Identity, paths, recording parameters |
| `[analysis]` | Spike-detection thresholds and analysis type |
| `[analysis.visualisation]` | Plot ranges and snippet windows |
| `[settings]` | Timing and unit conventions |
| `[stimulus.OU]` | Ornstein–Uhlenbeck process parameters |

---

## Top-Level Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `version` | string | current release | Package version that created the file. **Do not change.** |
| `master_seed` | int | fixed | Global seed for the PCG64DXSM generator. **Do not change.** |
| `n_seeds_per_setup` | int | 1 000 000 | Number of unique seeds allocated per setup. **Do not change.** |
| `current_seed_index` | int | 0 | Tracks how many seeds have been consumed. Updated automatically. |
| `setup_id` | int | — | Positive integer (1–20) identifying this setup. Must be unique across all distributed setups. |
| `setup_info` | string | — | Short human-readable description of the setup. |
| `config_file_creator` | string | — | Name of the person who created this configuration. |
| `creation_time` | string | — | Timestamp when the file was generated. |
| `out_dir` | string | `""` | Directory where generated `.abf` stimulus files are saved. |
| `input_dir` | string | `""` | Directory containing patch clamp recordings for analysis. |
| `stimulus_type` | string | `"OU"` | Type of stimulus to generate. Currently only `"OU"` (Ornstein–Uhlenbeck) is supported. |
| `n_sweeps` | int | `-1` | Number of sweeps per generated file. Set via CLI (`--n_sweeps`) or here. `-1` means "not set". |
| `sampling_rate` | int | `-1` | Sampling rate in Hz. Must match the acquisition system. `-1` means "not set". |
| `duration` | float | `-1` | Duration of each sweep in seconds. `-1` means "not set". |
| `backup_dir` | string | `""` | Where backup copies of generated stimuli are stored. Defaults to a subdirectory of `out_dir` when empty. |
| `analysis_dir` | string | `""` | Where analysis results (figures, logs) are saved. Defaults to `input_dir` when empty. |

> **Tip:** Parameters marked `-1` or `""` *must* be provided either in the
> config file or via the command-line interface before running a generation or
> analysis command.

---

## `[analysis]` — Spike Detection

These parameters control the peak-finding algorithm used during online
analysis.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `type` | list[str] | `["mini_sta"]` | Analysis pipeline(s) to run. Currently only `"mini_sta"` is implemented. |
| `refractory_period` | float | `0.001` | Refractory period in seconds, used for the LvR (local variation ratio) calculation. |
| `min_spike_height` | float | `-5` | Minimum peak height in mV for `scipy.signal.find_peaks`. Peaks below this threshold are ignored. |
| `fraction_min_spike_distance` | float | `0.8` | Minimum distance between two peaks, expressed as a fraction of `refractory_period`. The actual distance in samples is `fraction_min_spike_distance × refractory_period × sampling_rate`. |
| `visualise_results` | bool | `true` | Whether to produce a three-panel figure (trace, ISI histogram, spike snippets) for each sweep. |

---

## `[analysis.visualisation]` — Plot Parameters

These settings only take effect when `visualise_results = true`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `trace_duration` | float | `20` | Duration (in seconds) of the voltage trace shown in the overview panel. |
| `trace_start` | float | `0` | Start time (in seconds) of the overview trace window. |
| `isi_bin_max` | float | `1` | Right edge of the ISI histogram in seconds. |
| `isi_bin_width` | float | `0.25` | Bin width for the ISI histogram in seconds. |
| `interval_before_peak` | float | `0.0015` | Time before each peak to include in spike snippets (seconds). |
| `interval_after_peak` | float | `0.0035` | Time after each peak to include in spike snippets (seconds). |
| `snippet_ylim` | list[float] | `[-50, 30]` | Y-axis limits (mV) for the spike snippet panel. |

---

## `[settings]` — Timing and Units

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `wait_time` | int | `30` | Seconds to wait between stimulus generation and the start of analysis, giving the acquisition software time to save the recording. |
| `update_interval` | int | `5` | Seconds between successive checks for new recording files during online analysis. |
| `input_units` | string | `"pA"` | Physical unit of the generated stimulus. Currently fixed to picoamperes. |

---

## `[stimulus.OU]` — Ornstein–Uhlenbeck Process

Parameters for the exact Ornstein–Uhlenbeck process used to generate the
input current.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `mu` | float | `0.0` | Mean of the OU process in pA. The stimulus fluctuates around this value. |

> **Note:** Additional OU parameters (time constant τ, noise amplitude σ) are
> currently set internally by the generation code and cannot be overridden
> from the configuration file. This may change in a future release.

---

## Editing Tips

- Always use a text editor that preserves TOML syntax (e.g. VS Code with a
  TOML extension).
- **Never change** `version`, `master_seed`, or `n_seeds_per_setup` — these
  ensure reproducibility across distributed setups.
- After editing, you can verify the file with:
  ```bash
  python -c "import tomli; tomli.load(open('setup_1.toml', 'rb'))"
  ```
- If you need to start fresh, re-run `pydg_new_setup` to generate a new
  configuration interactively.
