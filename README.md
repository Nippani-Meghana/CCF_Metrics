# XOR Neural Network Metrics Pipeline

A refactored, network-agnostic evaluation pipeline for comparing simulated neural network recordings against a ground truth reference. Built around a centralised HDF5 data format and a role-driven helper function layer that eliminates all hardcoded neuron references.

---

## Overview

This pipeline evaluates a 35-neuron XOR network across 40 trials (10 repetitions × 4 input patterns) using 13 neurophysiological metrics. It compares a **Ground Truth (GT)** recording against a **Submission (SUB)** recording and produces per-pattern, per-neuron, and aggregate scores.

The pipeline was redesigned from an earlier 5-neuron, 400-trial system with hardcoded column names and a monolithic preprocessing cell. The new design stores all data in a structured HDF5 format and resolves neuron identity at runtime via role queries, making the entire metric suite reusable for any circuit topology.

---

## Network Architecture

| Neuron ID | Label     | Role             | Input Channel |
|-----------|-----------|------------------|---------------|
| 4         | E         | output           | —             |
| 9         | Int_A     | interneuron      | —             |
| 13        | Int_B     | interneuron      | —             |
| 15        | PyrMid_A  | intermediate     | —             |
| 16        | PyrMid_B  | intermediate     | —             |
| 25        | PyrIn_B1  | input            | 2             |
| 27        | PyrIn_A   | input            | 1             |
| 30        | PyrIn_B2  | input            | 2             |
| 0–34 (rest) | neuron_N | extended_network | —           |

**XOR Truth Table:**

| Case    | Input A | Input B | Expected E Output |
|---------|---------|---------|-------------------|
| XOR_00  | 0       | 0       | 0                 |
| XOR_10  | 1       | 0       | 1                 |
| XOR_01  | 0       | 1       | 1                 |
| XOR_11  | 1       | 1       | 0                 |

---

## Simulation Parameters

| Parameter        | Value                          |
|------------------|--------------------------------|
| Trial duration   | 100 ms                         |
| Repetitions      | 10                             |
| Total trials     | 40 (10 reps × 4 patterns)      |
| Total recording  | 5000 ms (4000 ms used, 1000 ms cooldown clipped) |
| Sampling rate    | 1000 Hz (1 ms resolution)      |
| Spiking neurons  | 8 (runtime-derived, not assumed) |
| Extended network | 27 neurons (subthreshold)      |

---

## Repository Structure

```
project/
│
├── output/
│   ├── GT/
│   │   ├── groundtruth-Vm.csv          # Raw membrane potential (long format)
│   │   ├── groundtruth-spikes.csv      # Raw spike times (float precision)
│   │   ├── trial_map.json              # Shared — trial timing and pattern labels
│   │   └── network_config.json         # Shared — neuron roles and IO channels
│   │
│   ├── SUB/
│   │   ├── submission-Vm.csv
│   │   └── submission-spikes.csv
│   │
│   ├── GT_h5/
│   │   └── groundtruth.h5              # Built by build_h5.py — STATUS: COMPLETE
│   │
│   └── SUB_h5/
│       └── submission.h5               # Built by build_h5.py — STATUS: PENDING; Currently using GT as SUB
│
├── build_h5.py                         # HDF5 builder — run once per recording pair
└── in_domain_metrics.ipynb             # Metrics notebook — STATUS: REFACTOR IN PROGRESS
```

---

## HDF5 File Structure

Both `groundtruth.h5` and `submission.h5` share an identical structure:

```
file.h5
│
├── /network_config     DataFrame — 35 rows
│     neuron_id | label | role | input_channel
│
├── /trial_map          DataFrame — 40 rows
│     trial_id | rep | case | t_start | t_end | input_ch1 | input_ch2
│
├── /data               DataFrame — 4000 rows (1 row per ms, cooldown clipped)
│     Context  (7):   t_ms | trial_id | t_in_trial | rep | case | input_ch1 | input_ch2
│     Vm       (35):  E_vm | PyrIn_A_vm | ... | neuron_0_vm | ...
│     Spike    (35):  E_spike | PyrIn_A_spike | ... | neuron_0_spike | ...
│
├── /spikes_raw         DataFrame — one row per spike event
│     neuron_id | label | spike_time_ms | trial_id | t_in_trial | rep | pattern
│     (spike_time_ms is float precision — never snapped to ms grid)
│
└── /metadata           HDF5 group attributes (scalar values)
      fs_hz | t_total_ms | n_trials | trial_len_ms | n_neurons_total | n_neurons_spiking
```

### Key Design Decisions

- **`/data` spike columns are snapped to 1 ms grid** — used for binary operations, raster plots, cross-correlation, PSTH
- **`/spikes_raw` preserves float precision** — used for ISI, van Rossum, Schreiber, KS where timing accuracy matters
- **Cooldown (4000–5000 ms) is clipped** during build — metrics never see it
- **`trial_map.json` and `network_config.json` are shared** between GT and SUB — only the Vm and spike CSVs differ

---

## Helper Functions

Defined once in Cell 3 of the metrics notebook. Replace all hardcoded column names and trial-grouping logic from the old pipeline.

```python
get_neurons(cfg, role=None, input_channel=None)
```
Returns a list of neuron label strings matching the given role or input channel. Supports single roles, lists of roles, `"all"`, and channel filtering.

```python
get_spiking_neurons(cfg, data)
```
Checks spike columns at runtime and returns labels where the spike column sum > 0. Always runtime-derived — never assumed from config — so it catches perturbed networks where new neurons may start firing.

```python
get_spike_cols(cfg, data)
```
Calls `get_spiking_neurons()` and returns the corresponding `_spike` column name strings.

```python
get_vm_cols(cfg, scope="all")
```
Returns `_vm` column name strings. `scope="all"` gives all 35 neurons; `scope="active"` gives only the 8 role-assigned neurons.

```python
get_trial(data, trial_id)
```
Returns a 100-row DataFrame for the specified trial ID.

```python
get_trials_by_pattern(data, pattern)
```
Returns a list of 10 DataFrames (one per repetition) where `case == pattern`.

```python
load_metadata(h5_path)
```
Reads `/metadata` group attributes via `h5py` and returns a plain Python dictionary.

---

## Metrics

All metrics also read `/network_config` for role queries and `/trial_map` for pattern grouping.

---

## Design Rules

1. **No hardcoded neuron names in any metric**
   ```python
   # Never
   df["E_spike"]
   # Always
   df[get_neurons(cfg, role="output")[0] + "_spike"]
   ```

2. **Spiking neuron set is always runtime-derived**
   ```python
   # Never assume a fixed set
   # Always
   get_spiking_neurons(cfg, data)
   ```

3. **Non-spiking neurons have spike cols = 0, not NaN**
   `0` means "did not fire". `NaN` would mean "unknown".

4. **`trial_map.json` and `network_config.json` are shared between GT and SUB**
   Only the Vm CSV and spikes CSV differ between recordings.

5. **Metrics requiring timing precision must use `/spikes_raw`**
   Spike times in `/data` are snapped to 1 ms. Float precision is only in `/spikes_raw`.

6. **`build()` is the only public method of `build_h5`**
   Never call process or build methods individually in production.

7. **The pipeline generalises to any circuit**
   Swap `network_config.json`, regenerate CSVs, rebuild HDF5. No changes to `build_h5.py` or the metrics notebook.

---

## Self-Consistency Test

Before comparing GT vs SUB, validate every metric by pointing both paths at the same file:

```python
GT_H5  = "output/GT_h5/groundtruth.h5"
SUB_H5 = "output/GT_h5/groundtruth.h5"   # Same file
```

Expected perfect scores:

| Metric                | Expected Value     |
|-----------------------|--------------------|
| Van Rossum distance   | 0.0                |
| Schreiber similarity  | 1.0                |
| KS statistic          | 0.0                |
| PSTH correlation      | 1.0                |
| Granger adjacency     | Identical matrix   |
| Behavioral accuracy   | 100%               |
| ISI Wasserstein       | 0.0                |
| Membrane potential RMS| 0.0                |
| Cross correlation     | 1.0                |

Any metric that does not return its perfect value indicates a bug in that metric's logic, not in the data.

---

## What Was Replaced

| Old                          | New                                      |
|------------------------------|------------------------------------------|
| `_read_trials_new()`         | `pd.read_hdf()` — data already in HDF5  |
| `_infer_fs_hz()`             | `metadata["fs_hz"]`                     |
| `_detect_pulse()`            | Not needed — patterns in trial_map.json |
| `_detect_anywhere()`         | Not needed                               |
| `_derive_meta()`             | Not needed — trial context in /data     |
| `_concat_with_context()`     | Not needed — /data already concatenated |
| `_pattern_counts()`          | `tmap["case"].value_counts()`           |
| `_pattern_confusion()`       | Not needed — shared trial_map guarantees alignment |
| `CANON_COLS`, `SPIKE_COLS`   | `get_spike_cols(cfg, data)`             |
| `VM_COLS`, `VM_MAP`          | `get_vm_cols(cfg, scope=...)`           |
| `INPUTS_MAP`, `OUTPUTS_MAP`  | `get_neurons(cfg, role=...)`            |
| `METRIC_VARS_NEW` dict       | Direct HDF5 reads per metric            |
| Entire preprocessing cell    | Deleted                                  |
