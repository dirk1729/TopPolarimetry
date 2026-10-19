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

## Verified on-site (probe job, 2026-10-13, worker c080)
- Workers are AlmaLinux 9.8 (native EL9): no OS classad needed, and
  `--config container=none` (native `setupATLAS`) works for the full chain.
- `/cvmfs/atlas.cern.ch` is mounted on workers.
- `/home/<user>/...` is visible from workers, so the repo can stay in `/home`
  (submit/log files on shared FS work).
- `apptainer`/`singularity` are not on the worker's default PATH.
- `getenv = False` means no `X509_USER_PROXY` in the job; only relevant if a
  rule needs grid data access.
- Login-node `python3` is 3.9 (see setup below for the Snakemake env).

## Differences from the lxplus version

- **Repo location.** No AFS needed. The repo lives under `/home/<user>/` and
  the workers see it, so submit/log files there work.
- **OS/container.** Workers are native EL9, so no OS classad and no container
  needed: run with `--config container=none` (native `setupATLAS`).
  `MY.WantOS` stays commented out in `condor_submit.py`.
- **Python/Snakemake.** The login-node `python3` is 3.9, and a venv built on
  `/usr/bin/python3.12` does **not** work, because the job scripts run
  `snakemake`'s python on the worker and workers lack `/usr/bin/python3.12`.
  Use a pixi env whose Python lives in `/home` (see setup below).
- **X.509 proxy.** Not forwarded by default (the chain needs no grid data
  access, and `condor_submit` fails outright if the proxy in your shell has
  expired). Set `CONDOR_FORWARD_PROXY=1` to pass `X509_USER_PROXY` through.
- **Still unknown: accounting group.** Submissions work without one so far;
  add an `accounting_group` classad to `lines = [...]` in `condor_submit.py`
  if the pool ever rejects or deprioritises jobs for lacking it.
- **`jobs: 50` in `config.yaml`.** A conservative guess, not a known quota.

## One-time setup

```bash
mkdir -p ~/snakemake-env && cd ~/snakemake-env
pixi init .
pixi add "python=3.12"
pixi add --pypi snakemake snakemake-executor-plugin-cluster-generic
chmod +x <repo>/profiles/uchicago/*.py
```

`snakemake` is not on conda-forge, hence the PyPI install inside the pixi env.

## Running

Start from a clean shell (not after `setupATLAS`/`asetup`) and run under
`tmux`/`nohup`, since it blocks until every job finishes. Put the target
**before** `--config` (which swallows following positional arguments), and
unset `PYTHONPATH` so the ATLAS python paths do not leak in:

```bash
cd <repo>
E=$HOME/snakemake-env/.pixi/envs/default
run() { env -u PYTHONPATH PATH=$E/bin:$PWD/profiles/uchicago:/usr/bin:/bin "$@"; }
run snakemake -n all --profile profiles/uchicago --config container=none   # dry run
run nohup snakemake all --profile profiles/uchicago --config container=none \
    splitting='{nJobs: 5, eventsPerJob: 100}' > logs/snakemake.log 2>&1 &
```

`configs/config.yaml` is at debug scale (`nJobs: 1, eventsPerJob: 10`); set
`splitting` inline as above (or edit the file) for real runs. Changing the
splitting does not by itself make Snakemake redo existing outputs: add
`--forceall` when re-running at a different scale.

Monitoring: `condor_q -batch` shows jobs grouped by rule, and per-job
stdout/stderr/submit-file are in `logs/condor/<rule>_<wildcards>.{out,err,sub,log}`.
The `.err` files only contain Snakemake's own wrapper output; the payload
(Athena) output is in the `.out` files and each job directory's `log.*`.

## Known issues
- `derivationPHYS` must run single-threaded (`threads: 1` in
  `configs/config.yaml`): with 4 threads, Athena 24.0.62 segfaults in
  `EGammaClusterCoreCellRecovery::findMaxECell`.
- Run-time verified on a 1 job x 10 event chain (L polarization, all 9 jobs
  succeeded). Memory/runtime requests are untested at larger scale.
