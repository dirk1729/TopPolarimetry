# HTCondor profile (lxplus)

Submits every pipeline rule as its own HTCondor job. Resources come from the
`resources:` block of `configs/config.yaml`: `threads` sets `request_cpus`,
`mem_mb` sets `request_memory`, and `runtime` (minutes) sets `+MaxRuntime`.
Condor logs and submit files are written to `logs/condor/`.

## One-time setup on lxplus

```bash
# Put the repo on AFS (condor refuses submit/log files on EOS). The
# 100 GB AFS workspace is a good place for it.
cd /afs/cern.ch/work/d/dallen && git clone <repo> toppolarimetry

# Install Snakemake (>= 8, which needs Python >= 3.11) and the generic
# cluster executor plugin in a plain venv on AFS. Don't use an LCG/asetup
# Python: the worker-side jobscript reuses this interpreter, and it has to
# run outside any ATLAS environment. If `python3 --version` on lxplus is
# older than 3.11, use `python3.11`/`python3.12` or a conda/miniforge Python.
python3.12 -m venv ~/venvs/snakemake
~/venvs/snakemake/bin/pip install snakemake snakemake-executor-plugin-cluster-generic
chmod +x profiles/htcondor/*.py
```

## Running

Start Snakemake from a clean shell, **not** after `setupATLAS`/`asetup`. It
keeps running until every job has finished, so run it under `tmux` on a fixed
lxplus node (e.g. `ssh lxplus9xx.cern.ch`, whichever node you are on) or with
`nohup`:

```bash
source ~/venvs/snakemake/bin/activate
cd /afs/cern.ch/work/d/dallen/toppolarimetry
snakemake -n --profile profiles/htcondor all          # dry run
snakemake --profile profiles/htcondor all
snakemake --profile profiles/htcondor --config splitting='{nJobs: 50, eventsPerJob: 200}' daod_phys
```

Large ROOT outputs can go to EOS: set `paths.storage_base` to
e.g. `/eos/user/d/dallen/toppol`. When the container is used, that path is
bind-mounted into it. On the EL9 batch nodes you can also set
`container: none` to skip apptainer entirely.

Monitoring: `condor_q -batch` shows jobs grouped by rule, and per-job
stdout/stderr is in `logs/condor/<rule>_<wildcards>.{out,err}`.
