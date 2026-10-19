#!/usr/bin/env python3
"""Snakemake --cluster submit hook for HTCondor, adapted from
profiles/htcondor/ (written for CERN lxplus) for the UChicago Analysis
Facility. See profiles/uchicago/README.md for what's been verified here
vs. still needs confirming on-site.

Snakemake calls this with the path of a generated jobscript; we wrap it in a
submit description, hand it to condor_submit and print the cluster id, which
Snakemake later passes to condor_status.py / condor_rm.
"""
import json
import os
import re
import subprocess
import sys

LOG_DIR = os.path.join("logs", "condor")

# Fallbacks for rules without explicit resources in configs/config.yaml
DEFAULTS = {"threads": 1, "mem_mb": 2000, "runtime": 120}


def read_job_properties(jobscript):
    # Same format snakemake.utils.read_job_properties parses; done by hand so
    # this script works with any python3, not only the one Snakemake is in.
    with open(jobscript) as f:
        for line in f:
            if line.startswith("# properties = "):
                return json.loads(line[len("# properties = "):])
    raise RuntimeError(f"no job properties found in {jobscript}")


def job_name(props):
    if props.get("type") == "group":
        name = f"group_{props.get('groupid', 'job')}"
    else:
        name = props.get("rule", "job")
        wildcards = props.get("wildcards", {})
        if wildcards:
            name += "_" + "_".join(f"{k}{v}" for k, v in sorted(wildcards.items()))
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def main():
    jobscript = os.path.abspath(sys.argv[-1])
    props = read_job_properties(jobscript)
    resources = props.get("resources", {})

    threads = props.get("threads") or DEFAULTS["threads"]
    mem_mb = resources.get("mem_mb") or DEFAULTS["mem_mb"]
    runtime = resources.get("runtime") or DEFAULTS["runtime"]

    os.makedirs(LOG_DIR, exist_ok=True)
    name = job_name(props)
    log = os.path.join(os.path.abspath(LOG_DIR), name)

    lines = [
        "universe       = vanilla",
        f"executable     = {jobscript}",
        f"initialdir     = {os.getcwd()}",
        "getenv         = False",
        f"request_cpus   = {threads}",
        f"request_memory = {mem_mb}",
        # lxplus used `+MaxRuntime` (seconds) + `MY.WantOS = "el9"` to pick
        # EL9 worker nodes with a wall-time cap; neither is verified to mean
        # anything on UChicago's pool. Left as a seconds-based cap in case
        # the site honors it (harmless if not: an unrecognized custom
        # classad is just inert, not an error) - but the actual OS/container
        # selection mechanism needs to be confirmed on-site (see README) and
        # filled in below once known.
        f"+MaxRuntime    = {int(runtime) * 60}",
        # 'MY.WantOS      = "el9"',  # TODO(uchicago): replace with whatever
        #                            # this site actually uses, if anything.
        f"batch_name     = {props.get('rule', 'snakemake')}",
        f"output         = {log}.out",
        f"error          = {log}.err",
        f"log            = {log}.log",
    ]
    # Opt-in: the simulation chain needs no grid data access, and condor_submit
    # refuses to submit at all when the proxy in the env has expired.
    proxy = os.environ.get("X509_USER_PROXY")
    if proxy and os.environ.get("CONDOR_FORWARD_PROXY") == "1":
        lines.append(f"x509userproxy  = {proxy}")
    lines.append("queue 1")

    sub_path = f"{log}.sub"
    with open(sub_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    result = subprocess.run(
        ["condor_submit", "-terse", sub_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode)
    # -terse prints "<cluster>.0 - <cluster>.0"
    print(result.stdout.split()[0].split(".")[0])


if __name__ == "__main__":
    main()
