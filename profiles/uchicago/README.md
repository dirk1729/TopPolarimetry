# HTCondor profile (UChicago Analysis Facility)

Adapted from `profiles/htcondor/` (written for CERN lxplus). Submits every
pipeline rule as its own HTCondor job, same as that profile. Resources come
from the `resources:` block of `configs/config.yaml`: `threads` sets
`request_cpus`, `mem_mb` sets `request_memory`, `runtime` (minutes) sets
`+MaxRuntime`. Condor logs and submit files are written to `logs/condor/`.

## What's carried over unchanged
- `condor_status.py` - pure `condor_q`/`condor_history` polling, nothing
  site-specific in it.
- The overall submit-description shape in `condor_submit.py` (`universe`,
  `request_cpus`, `request_memory`, log/out/err/sub file layout).

## What's different from the lxplus version, and still needs confirming on-site
- **Repo location.** lxplus requires AFS specifically (condor there refuses
  submit/log files on EOS). UChicago doesn't have AFS; this repo has been
  living under `/data/<your-username>/...` there in past sessions (see your
  own `~/.ssh/config` `uchicago` host entry for the real path/username) -
  local `/data` storage should be fine for submit/log files, but confirm
  there isn't an equivalent restriction on this site's shared filesystems
  before relying on it for a large run.
- **OS/container selection.** lxplus used a custom classad
  (`MY.WantOS = "el9"`) to land on EL9 worker nodes. That line is commented
  out in `condor_submit.py` here rather than guessed at - **this is the main
  open item**. Find out (site docs, or ask UChicago AF support) whether:
  - worker nodes are already uniformly a usable OS/container for
    `Sim_tf.py`/`Reco_tf.py` etc. (in which case nothing is needed), or
  - the site wants a `+SingularityImage`/`+ContainerImage` classad, or an
    equivalent of lxplus's apptainer wrapping (the Snakefile's
    `alrb_container_run()` already runs each payload through
    `atlasLocalSetup.sh -c el9`, so this may be a non-issue - needs
    verifying for real rather than assumed).
- **Accounting / fairshare group.** Not set at all currently. If UChicago's
  pool requires an `accounting_group` (or similar) classad to submit, add it
  to the `lines = [...]` list in `condor_submit.py`.
- **Python version for Snakemake.** lxplus's instructions build a venv with
  `python3.12` because lxplus's default Python is too old for Snakemake >= 8.
  Check `python3 --version` on a UChicago AF login node before assuming the
  same workaround is (or isn't) needed.
- **X.509 proxy.** `condor_submit.py` still passes through `X509_USER_PROXY`
  if set, since ATLAS data access (Rucio/XRootD) commonly needs one
  regardless of site - confirm how to obtain one on UChicago's AF if you
  don't already have a working `voms-proxy-init`/similar in your shell.
- **CVMFS.** The Snakefile's `asetup`/`Gen_tf.py`/etc. calls need
  `/cvmfs/atlas.cern.ch` on the worker nodes. UChicago AF being an official
  ATLAS facility should have this, but it hasn't been verified from inside
  this repo/session - check before a large submission, not after.
- **`jobs: 50` in `config.yaml`.** A conservative starting guess, not a
  known quota. Raise it once you know your real allocation.

## One-time setup (sketch - fill in once the above is confirmed)

```bash
# Wherever the repo lives on UChicago's storage (see "Repo location" above)
cd /data/<your-username>/toppolarimetry   # adjust to the real path
python3 -m venv ~/venvs/snakemake   # or python3.11/3.12 if default python3 is older
~/venvs/snakemake/bin/pip install snakemake snakemake-executor-plugin-cluster-generic
chmod +x profiles/uchicago/*.py
```

## Running

Same pattern as the lxplus profile - start from a clean shell (not after
`setupATLAS`/`asetup`), and run under `tmux`/`nohup` since it blocks until
every job finishes:

```bash
source ~/venvs/snakemake/bin/activate
cd /data/<your-username>/toppolarimetry
snakemake -n --profile profiles/uchicago all          # dry run first
snakemake --profile profiles/uchicago all
snakemake --profile profiles/uchicago --config splitting='{nJobs: 50, eventsPerJob: 200}' daod_phys
```

`configs/config.yaml` is still at debug scale (`nJobs: 1, eventsPerJob: 10`)
as of this writing - bump `splitting` (inline via `--config` like above, or
edit the file) before a real production submission.

Monitoring: `condor_q -batch` shows jobs grouped by rule, and per-job
stdout/stderr/submit-file are in `logs/condor/<rule>_<wildcards>.{out,err,sub,log}`.
