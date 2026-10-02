## Quick Start
Clone the repo:
```
git clone https://github.com/dirk1729/TopPolarimetry.git
```

## How To Generate Datasets

Samples are produced by a Snakemake workflow (`Snakefile` + `configs/config.yaml`)
that drives the full ATLAS MC chain — MadGraph+Pythia8 generation, Geant4
simulation, digitization, reconstruction, and DAOD_PHYS derivation — via
official ATLAS releases over CVMFS. There's nothing to build locally for
this step; `asetup` resolves each release on demand.

### Prerequisites
- CVMFS access to `/cvmfs/atlas.cern.ch` (ATLASLocalRootBase), and an `el9`
  host or `apptainer` available — the workflow runs each stage inside an
  `el9` container by default (set `container: none` in `configs/config.yaml`
  to run natively on an already-el9 host).
- `snakemake` (e.g. `pip install snakemake` inside a conda env).

### Configure
Edit `configs/config.yaml`:
- `polarizations`: which of `U` / `L` / `R` to produce.
- `splitting`: `nJobs` and `eventsPerJob` per polarization.
- each stage's `asetupRelease`, plus simulation's `conditionsTag` /
  `geometryVersion` / `simulator` / `physicsList`.
- `paths.storage_base`: set this to move bulky outputs (EVNT/HITS/RDO/AOD)
  outside the repo, e.g. onto EOS; job options and `MCValidation` always
  stay local.

### Run
```
snakemake --cores <N> daod_phys
```
produces `Derivation/<pol>_ttbar_PHYS/DAOD_PHYS.mcval.pool.root` for each
configured polarization — the file the TopCPToolkit step below consumes.

Other useful targets:
- `snakemake --cores <N> daod_files` — just TRUTH1/TRUTH3 from EVNT
  (skips the full Geant4 sim/digi/reco chain, much faster).
- `snakemake --cores <N>` (or `... all`) — `daod_phys` plus the
  truth-level `MCValidation` histograms.
- A Snakemake profile for HTCondor batch submission is in
  `profiles/htcondor/`.

## How To Build & Run TopCPToolkit

This turns a `DAOD_PHYS.mcval.pool.root` from the step above into the
reco-level ntuple (`jet_constituent_trk_*`, `spin_MySpin_cos_theta_helicity_*`,
etc.) that `model/DataLoader_TopCPToolkit.py` reads. It's a separate ATLAS
analysis package (`TopPolarimetry`) layered onto the shared TopCPToolkit
framework, both kept outside this repo's git history (`TopCPToolkit/` is
gitignored) since they're independently-versioned CERN GitLab checkouts.

1. Clone the framework:
   ```
   git clone https://gitlab.cern.ch/atlas/amg/software/TopCPToolkit.git
   ```
2. Inside `TopCPToolkit/source`, clone the analysis package:
   ```
   git clone https://gitlab.cern.ch/sbergner/toppolarimetry.git TopPolarimetry
   ```
3. Build, from the `TopCPToolkit/` top level:
   ```
   source source/TopPolarimetry/scripts/setup_stable.sh
   source source/TopPolarimetry/scripts/full_compile.sh
   ```
   (`quick_compile.sh` for incremental rebuilds after editing existing
   files; `setup_restore.sh` to restore a previously-built working area.)
4. Run the event loop:
   ```
   runTop_el.py -t TopPolarimetry -p TopPolarimetry/configs mc/reco.yaml \
       --inputFiles <DAOD_PHYS.mcval.pool.root> --submitDir run/<name>
   ```
   See `source/TopPolarimetry/README.md` and the
   [TopCPToolkit docs](https://topcptoolkit.docs.cern.ch/latest/starting/installation/)
   for the full option set.

## How To Run The Model (TopCPToolkit / Reco-Level Samples)

Starting from a reco-level ROOT file produced above (or any file matching
the schema in `model/DataLoader_TopCPToolkit.py`'s docstring):

Activate the `toppol` conda environment and work from `model/`:
```
conda activate toppol
cd model
```

1. **Preprocess** each reco ROOT file into a per-file dataset:
   ```
   python DataLoader_TopCPToolkit.py <input.root> <dataset_dir>/run_<N>/dataset.pt
   ```
2. **Combine** the per-file datasets:
   ```
   python Combine_DataSets.py <tag> <num_files> <dataset_dir>
   ```
3. **Train**:
   ```
   python New_Training.py <tag> <epochs> <embed_dim> <dir_dataset> <dir_training>
   ```
4. **Evaluate** a checkpoint on the held-out test split:
   ```
   python New_Eval.py <dir_dataset> <dir_training> <model_path>
   ```
5. **Run inference** on a new sample the model wasn't trained/validated on:
   ```
   python Run_Inference.py <dataset_path> <model_path> [out_dir]
   ```

See [model/README.md](model/README.md) for full argument descriptions,
worked examples, the model's input tensors, and known gaps (in
particular: pick a checkpoint from before the model overfits, not
necessarily `model_final.torch` — `model/README.md` explains how).

## Dependencies
Developed on Ubuntu, using CVMFS-provided ATLAS software — there's no
longer a local build step for the simulation chain itself.

<ul>
  <li>CVMFS access to <code>/cvmfs/atlas.cern.ch</code> (ATLASLocalRootBase), and <code>apptainer</code> or an el9 host</li>
  <li>python3 + <code>snakemake</code>, for the dataset-generation workflow</li>
  <li>conda, for the <code>toppol</code> environment the model pipeline runs in (PyTorch, uproot, awkward, scikit-learn, matplotlib)</li>
  <li>CERN GitLab / Kerberos access, to clone TopCPToolkit and the TopPolarimetry analysis package</li>
</ul>
