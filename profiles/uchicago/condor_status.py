#!/usr/bin/env python3
"""Snakemake --cluster-status hook for HTCondor.

Prints running, success or failed for the given cluster id.
"""
import subprocess
import sys

# HTCondor JobStatus codes
IDLE, RUNNING, REMOVED, COMPLETED, HELD, TRANSFERRING, SUSPENDED = range(1, 8)


def query(cmd):
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.split()


def main():
    cluster = sys.argv[1]

    fields = query(["condor_q", cluster, "-af", "JobStatus"])
    if fields is None:
        # schedd hiccup: don't declare the job dead, ask again next round
        print("running")
        return
    if fields:
        status = int(fields[0])
        # Held jobs never finish on their own (usually memory/runtime limits)
        print("failed" if status in (HELD, REMOVED) else "running")
        return

    fields = query(["condor_history", cluster, "-limit", "1", "-af", "JobStatus", "ExitCode"])
    if not fields:
        # Just left the queue and not yet in the history
        print("running")
        return
    status = int(fields[0])
    exit_code = fields[1] if len(fields) > 1 else "undefined"
    print("success" if status == COMPLETED and exit_code == "0" else "failed")


if __name__ == "__main__":
    main()
