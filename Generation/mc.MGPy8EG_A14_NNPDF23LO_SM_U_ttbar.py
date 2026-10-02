import os
import sys
import stat
import glob
import subprocess

from MadGraphControl.MadGraphUtils import *
from MadGraphControl.MadGraph_NNPDF30NLO_Base_Fragment import *

include("Pythia8_i/Pythia8_A14_NNPDF23LO_EvtGen_Common.py")
include("Pythia8_i/Pythia8_aMcAtNlo_decayMEC.py")

safety = 1.1
nevents = runArgs.maxEvents * safety

process = """
import model sm
define p = g u c d s u~ c~ d~ s~
define j = g u c d s u~ c~ d~ s~
define l+ = e+ mu+
define l- = e- mu-
define vl = ve vm vt
define vl~ = ve~ vm~ vt~
generate p p > t t~ [QCD]
output -f
"""

process_dir = new_process(process)

run_settings = {
    'nevents': nevents,
    'parton_shower': 'PYTHIA8',
}
modify_run_card(runArgs=runArgs, process_dir=process_dir, settings=run_settings)

# Reweight card: LO matrix-element ratios applied to NLO events.
# Produces weight columns top_left and top_right alongside the central NLO weight.
# NOTE: {L}/{R} labels are incompatible with [QCD], hence the reweight approach.
reweight_card = """\
launch --rwgt_name=top_left
  change process p p > t{L} t~

launch --rwgt_name=top_right
  change process p p > t{R} t~
"""
reweight_path = os.path.join(process_dir, 'Cards/reweight_card.dat')
with open(reweight_path, 'w') as f:
    f.write(reweight_card)

# MadSpin must NOT be active during reweighting: MadGraph attempts to include
# the decay chain in the reweight ME and crashes with "No matrix elements
# generated".  Remove any pre-existing madspin card so generate() runs
# reweight-only, then apply MadSpin manually on the reweighted LHE below.
madspin_path = os.path.join(process_dir, 'Cards/madspin_card.dat')
if os.path.exists(madspin_path):
    os.unlink(madspin_path)

print_cards()

# Rewrite ~/.local/bin/f2py3 using the Python that is currently running this
# job option (the ATLAS/LCG Python with numpy+f2py in its stack).  The file
# on disk was installed for python3.8 which no longer exists on this host.
_f2py_wrapper = os.path.expanduser('~/.local/bin/f2py3')
with open(_f2py_wrapper, 'w') as _f:
    _f.write(f'#!/bin/bash\nexec {sys.executable} -m numpy.f2py "$@"\n')
os.chmod(_f2py_wrapper, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

# Step 1 — NLO generation + polarization reweighting (MadSpin OFF)
generate(process_dir=process_dir, runArgs=runArgs)

# Step 2 — MadSpin on the reweighted LHE
# MadSpin preserves all weight columns (central, top_left, top_right).
run_dir = os.path.join(process_dir, 'Events', 'run_01')
lhe_candidates = glob.glob(os.path.join(run_dir, 'unweighted_events.lhe.gz'))
if not lhe_candidates:
    lhe_candidates = glob.glob(os.path.join(run_dir, '*.lhe.gz'))
if not lhe_candidates:
    raise RuntimeError(f'No LHE file found in {run_dir} after generation')
lhe_file = lhe_candidates[0]

madspin_card = """\
decay t > b j j
decay t~ > b~ l- vl~
set Nevents_for_max_weight 75
set max_weight_ps_point 400
"""
with open(madspin_path, 'w') as f:
    f.write(madspin_card)

subprocess.run(
    [os.path.join(process_dir, 'bin/madspin'), lhe_file],
    check=True,
)

# arrange_output expects to find events at the standard location; replace the
# undecayed file with the MadSpin output so the shower reads decayed events.
decayed_lhe = os.path.join(run_dir, 'decayed_events.lhe.gz')
if os.path.exists(decayed_lhe):
    os.replace(decayed_lhe, lhe_file)

evgenConfig.description = 'NLO_semileptonic_ttbar_LR_polarization_reweighting'
evgenConfig.contact = ['Derrick Allen <derrick.ray.allen@cern.ch>']
evgenConfig.keywords += ['SM', 'ttbar', 'NLO']

arrange_output(process_dir=process_dir, runArgs=runArgs)
