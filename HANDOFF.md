# Handoff: continuing on UChicago

Context for picking this project up in a fresh Claude Code session on the
UChicago Analysis Facility. Written at commit `400c835` (the commit that
retired the old madgraph/pythia pipeline), with the UChicago batch-submission
profile added on top, uncommitted as of this file.

## What this project is

`TopPolarimetry` has two halves:
1. **Simulation**: a Snakemake workflow producing ttbar DAOD_PHYS samples
   (polarized or not) through the full ATLAS chain, then running them
   through TopCPToolkit + a custom `TopPolarimetry` analysis package to get
   a reco-level ntuple with the polarimetric angle and track-level truth.
2. **Model**: an attention-based PyTorch model (`model/`) that regresses the
   polarimetric angle cos θ directly from reconstructed jet/track/event
   features, without full kinematic reconstruction.

Read [README.md](README.md) top to bottom first - it covers both halves:
dataset generation (Snakemake), the TopCPToolkit build/run step, and the
model pipeline (preprocess → train → eval → infer). [model/README.md](model/README.md)
goes deeper on the model side specifically (tensor shapes, architecture,
known gaps, the overfitting/checkpoint-selection caveat).

## Repo layout, what's tracked vs. not

Tracked: `Generation/`, `Simulation/`, `Digitization/`, `Reconstruction/`,
`Derivation/`, `MCValidation/`, `Plotting/`, `Snakefile`, `configs/`,
`profiles/`, `model/`.

Gitignored (local build/run artifacts, regenerate per README instead of
expecting them from git):
- `TopCPToolkit/` - the framework + the nested `TopPolarimetry` analysis
  package (`source/TopPolarimetry/`), each its own CERN GitLab checkout.
  Remotes: `gitlab.cern.ch/atlas/amg/software/TopCPToolkit.git` (framework)
  and `gitlab.cern.ch/sbergner/toppolarimetry.git` (the analysis package -
  note the different owner, a collaborator).
- `envs/toppol` - a cloned copy of the `toppol` conda env (PyTorch+CUDA,
  uproot, awkward, scikit-learn, matplotlib). Clone fresh with
  `conda create --prefix ./envs/toppol --clone toppol` if coming from a
  machine that has the global `toppol` env, or build one from scratch -
  there's no `environment.yml` in the repo yet.
- `data/`, `training/` - preprocessed datasets and training runs from the
  model pipeline.
- Per-job simulation outputs (`Generation/*_ttbar/`, `Simulation/*_ttbar/`,
  etc.) - ROOT files, logs, asetup caches from actually running the
  Snakemake workflow.

A sibling GitLab repo (`gitlab.cern.ch/dallen/toppolarimetry`, note lowercase
vs. this repo's name) used to hold the Snakemake simulation workflow as its
own history; that history was dropped and its files copied directly into
*this* repo instead (see commit `400c835`'s message). If you go looking for
it expecting a live upstream to pull from, it won't have one - this repo is
now the source of truth for that workflow too.

## Immediate task: batch submission on UChicago

The user has compute allocation on UChicago's AF, not CERN lxplus, so that's
the chosen venue (decided over a prior lxplus-vs-UChicago discussion - lxplus
would've meant setting up AFS access from scratch, which doesn't exist
anywhere in this environment; UChicago access is already working and
exercised repeatedly in this session's shell history).

**Just added, not yet verified or run:** `profiles/uchicago/` - a Snakemake
HTCondor profile adapted from the existing `profiles/htcondor/` (which was
written for CERN lxplus specifically: AFS-only submit/log files, a
`MY.WantOS = "el9"` classad for CERN's pool). Read
[profiles/uchicago/README.md](profiles/uchicago/README.md) - it lists
exactly what was carried over unchanged (the generic HTCondor submit/status
mechanics) vs. what's CERN-specific and was either adapted or deliberately
left as an open question rather than guessed at:

- OS/container selection on UChicago's pool (lxplus's `MY.WantOS` classad is
  commented out, not replaced - needs a real answer from site docs/support)
- Whether UChicago requires an `accounting_group` classad to submit (not
  currently set)
- Default `python3` version on a UChicago AF login node (Snakemake >= 8
  needs >= 3.11; lxplus needed a workaround for this, UChicago might not)
- Confirming CVMFS (`/cvmfs/atlas.cern.ch`) is actually mounted on UChicago
  AF worker nodes (very likely, since it's an official ATLAS facility, but
  not independently confirmed from inside this repo/session)
- `configs/config.yaml` is still at debug scale (`nJobs: 1, eventsPerJob: 10`)
  - bump this before an actual production submission

Work through that list with the user before trusting a large submission;
none of it is guessed at in the profile itself, it's flagged as unknown on
purpose rather than silently assumed.

## Things worth knowing that aren't obvious from the code alone

- The model pipeline had two real bugs found and fixed this session, both
  worth re-checking if training results ever look wrong again:
  (1) input features (pT/mass/MET) were unnormalized relative to
  eta/phi/charge by 4-5 orders of magnitude, causing the model to collapse
  to a near-constant prediction - fixed in `DataLoader_TopCPToolkit.py` via
  `PT_SCALE`. (2) training with no early stopping / weight decay overfits
  within ~20 epochs on the current dataset size; always check
  `loss_curve_total.png`'s val-loss minimum and use that epoch's checkpoint,
  not `model_final.torch`, for anything you actually trust.
- `model/DataLoader_Parallel.py` is dead code (orphaned leftover from the
  retired truth-level pipeline) - don't be confused by it still being
  present.
- The `.pt` files this pipeline produces are plain pickles of whole
  `Dataset`/`Model` objects (not just weights/state dicts). They're brittle
  across code changes to the pickled classes themselves - this caused a real
  debugging session earlier. If `torch.load` ever throws an
  `AttributeError` on a `.pt`/`.torch` file that used to load fine, suspect
  a class-shape mismatch between when it was saved and the current code,
  not a corrupted file.
