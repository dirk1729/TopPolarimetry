# Model Pipeline: DataLoader → Training → Eval

This covers the **reco-level** pipeline: `DataLoader_TopCPToolkit.py` →
`Combine_DataSets.py` → `New_Training.py` → `New_Eval.py` →
`Run_Inference.py`. It consumes
reco ntuples produced by TopCPToolkit/TopPolarimetry (see
`source/TopPolarimetry/share/configs/mc/reco.yaml`), as opposed to the
Pythia truth-level pipeline described in the top-level [README.md](../README.md)
(`DataLoader_Parallel.py`, driven by `run_job.sh`), which is a separate,
unrelated pipeline not covered here.

## Prerequisites

- The `toppol` conda environment (PyTorch, uproot, awkward, scikit-learn,
  matplotlib):
  ```
  conda activate toppol
  ```
- A reco-level ROOT file with a `reco` TTree containing (at minimum) the
  branches `DataLoader_TopCPToolkit.py` reads: jet kinematics
  (`jet_pt_NOSYS`, `jet_eta`, `jet_phi`, `jet_e_NOSYS`,
  `jet_idx_down_from_thad`), jet-constituent tracks
  (`jet_constituent_trk_{pt,eta,phi,q,fromDown,fromUp,fromBottom}`),
  lepton/MET branches, the polarimetric angle
  (`spin_MySpin_cos_theta_helicity_{p,m}_NOSYS`, `t_isHadronic`), and the
  lep+jets selection flag (`pass_lepjets_LooseLH_NOSYS`). This is what a
  TopCPToolkit `reco.yaml` run over a DAOD_PHYS sample produces.

All commands below are run from `model/`.

## 1. Preprocess a ROOT file into a per-file dataset

```
python DataLoader_TopCPToolkit.py <input.root> <dataset_dir>/run_<N>/dataset.pt
```

- One call per input ROOT file; put each file's output in its own
  `run_<N>/` subdirectory (`N = 0, 1, 2, ...`) so `Combine_DataSets.py`
  can find them.
- Applies the lep+jets + probe-jet-matched selection, builds the probe
  jet / probe-jet-constituent / event tensors, and pickles a
  `CustomDataset` object to `dataset.pt`.

Example:
```
mkdir -p ../data/run_0
python DataLoader_TopCPToolkit.py /path/to/output.root ../data/run_0/dataset.pt
```

## 2. Combine per-file datasets

```
python Combine_DataSets.py <tag> <num_files> <dataset_dir>
```

- `<tag>` isn't used for anything except keeping the argument list
  consistent with the rest of the pipeline.
- `<num_files>` is how many `run_0 .. run_{num_files-1}` directories to
  load and concatenate (`ConcatDataset`).
- Writes `<dataset_dir>/dataset_combined.pt`.

Example (one run directory, `run_0`):
```
python Combine_DataSets.py first 1 ../data
```

## 3. Train

```
python New_Training.py <tag> <epochs> <embed_dim> <dir_dataset> <dir_training>
```

- `<tag>` is just used for print statements/logging context, not paths.
- `<dir_dataset>` must contain `dataset_combined.pt` from step 2.
- `<dir_training>` is created output — make sure `<dir_training>/models/`
  exists (or create it) before running.
- Splits the combined dataset into train/val/test (75/25, then the 25%
  split 20/80 into val/test) with a fixed seed (`42`), so the same test
  set is reproduced by `New_Eval.py` in step 4.
- Writes a checkpoint every epoch to
  `<dir_training>/models/model_Epoch_<N>.torch`, plus `model_final.torch`,
  loss-curve plots, and a test-set `costheta` validation plot, all in
  `<dir_training>`.

Example:
```
mkdir -p ../training/models
python New_Training.py first 10 4 ../data ../training
```

## 4. Evaluate a saved checkpoint

```
python New_Eval.py <dir_dataset> <dir_training> <model_path>
```

- Rebuilds the same train/val/test split as step 3 (same dataset dir,
  same seed), loads `<model_path>` (any epoch checkpoint or
  `model_final.torch`), and regenerates
  `<dir_training>/pred_1d_costheta.png` and `pred_2d_costheta.png` from
  the test set.
- Useful for re-plotting a specific epoch's predictions without
  retraining.

Example:
```
python New_Eval.py ../data ../training ../training/model_final.torch
```

## 5. Run inference on a new sample

```
python Run_Inference.py <dataset_path> <model_path> [out_dir]
```

- For scoring a dataset the model was never trained *or* validated on
  (e.g. a separate physics sample you want predictions for) — unlike
  `New_Eval.py`, it does **not** re-derive a train/val/test split; it runs
  the model on every event in `<dataset_path>`.
- `<dataset_path>` is a single `dataset.pt` (from step 1) or a combined
  `dataset_combined.pt` (from step 2) — anything holding a
  `DataLoader_TopCPToolkit.CustomDataset`-shaped dataset.
- `<model_path>` is any checkpoint (an early epoch, not necessarily
  `model_final.torch` — see the overfitting note below).
- `[out_dir]` is optional, defaults to `<dataset_path>`'s own directory.
- Prints per-event true vs. predicted `costheta`, plus overall R² and
  mean true/predicted values, and (when there's more than one event)
  saves `inference_1d_costheta.png` (true vs. predicted distributions)
  and `inference_2d_costheta.png` (per-event scatter of predicted vs.
  true `costheta` against the `y = x` line, with R² annotated) to
  `out_dir`. The 2D plot uses a scatter rather than `New_Eval.py`'s
  100-bin `hist2d`, since inference sets are often too small for a
  binned heatmap to be legible.

Example:
```
python Run_Inference.py ../data/polarized/run_0/dataset.pt ../training/models/model_Epoch_20.torch
```

**Picking a checkpoint:** with the current training setup (no early
stopping / weight decay), the model tends to overfit well before
`model_final.torch`'s epoch — check `<dir_training>/loss_curve_total.png`
for where val loss bottoms out and use that epoch's checkpoint from
`<dir_training>/models/`, not the final one.

## Model inputs

The model (`Model.forward` in `new_model.py`) takes three tensors, all
built by `DataLoader_TopCPToolkit.py`:

| Tensor | Shape | Contents |
|---|---|---|
| `probe_jet` | `[batch, 1, 4]` | `pT, eta, phi, mass` of the jet matched to the down-type quark from the hadronic top decay |
| `probe_jet_constituent` | `[batch, 200, 4]` | `pT, eta, phi, q` per ghost-associated track in the probe jet, sorted by pT, zero-padded/clipped to 200 |
| `event_tensor` | `[batch, 213, 4]` | Concatenation of probe jet (1 row) + probe jet constituents (200 rows) + lepton (1 row: `pT, eta, phi, q`) + MET (1 row: `MET, phi, 0, 0`) + up to 10 balance jets (`pT, eta, phi, 0`, sorted by pT) |

The model outputs a single 2-vector `costheta_output`, regressing the
polarimetric angle cosine (`costheta_labels` in the dataset).

## Known gaps

- The old truth-level pipeline (`DataLoader_Parallel.py`,
  `run_job.sh`, `New_Eval.py`'s previous 8-label version) is currently
  unexercised and may not be consistent with the rest of this pipeline.
- Everything above has only been verified on a small (~18-event) test
  file, not a full-scale production sample.
