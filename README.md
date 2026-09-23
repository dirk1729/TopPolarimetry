## Quick Start
Clone the repo:
```
git clone --recursive git@github.com:LukeV37/Top_Polarimetry.git
```

Ensure dependencies are met, and install the submodules:
```
./build_submodules.sh
```

Please be patient while submodules build...

## How To Generate Datasets

### Madgraph
To run madgraph simulation, run the following
```
cd madgraph
./run.sh
./post_process.sh
```
The lhe file file is generated, and the training labels are written to root file. 

### Pythia
To shower in pythia, run the following
```
cd pythia
./run.sh
```
The training data will be written to a root file. 

## How To Run The Model (TopCPToolkit / Reco-Level Samples)

This is a separate pipeline from the Madgraph/Pythia truth-level one
above. It starts from a reco-level ROOT file already produced by running
TopCPToolkit/TopPolarimetry's `reco.yaml` config over a DAOD_PHYS sample
(that ATLAS-software build/run step is outside this repo and not covered
here — see `model/DataLoader_TopCPToolkit.py`'s module docstring for the
expected ntuple schema).

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
Runs on most linux environments. Developed on Ubuntu 22.04.

Required Dependencies:
<ul>
  <li>python3</li>
  <li>ROOTv6</li>
  <li>g++</li>
  <li>gfortran</li>
  <li>gzip</li>
  <li>automake</li>
  <li>libtool</li>
  <li>autoconf</li>
</ul>
