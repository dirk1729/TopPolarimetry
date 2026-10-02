# Import all of the necessary methods to use MadGraph
from MadGraphControl.MadGraphUtils import *
from MadGraphControl.MadGraph_NNPDF30NLO_Base_Fragment import *

# Some includes that are necessary to interface MadGraph with Pythia
include("Pythia8_i/Pythia8_A14_NNPDF23LO_EvtGen_Common.py")
include("Pythia8_i/Pythia8_MadGraph.py")


# Number of events to produce
safety = 1.1 # safety factor to account for filter efficiency
nevents = runArgs.maxEvents * safety

process = """
import model sm
"""

# Define some multi-particle representations
process += """
define p = g u c d s u~ c~ d~ s~
define j = g u c d s u~ c~ d~ s~
define l+ = e+ mu+
define l- = e- mu-
define vl = ve vm vt
define vl~ = ve~ vm~ vt~
"""

# Define the physics process to be simulated
process += """
generate p p > t{L} t~, t > b j j, t~ > b~ l- vl~
"""

# This defines the MadGraph outputs
process += """
output -f
"""

# Define the process and create the run card from a template
process_dir = new_process(process)
settings = {'ickkw': 0, 'nevents':nevents}
modify_run_card(process_dir=process_dir,runArgs=runArgs,settings=settings)


generate(process_dir=process_dir,runArgs=runArgs)

# These details are important information about the JOs
evgenConfig.description = 'SM_semileptonic_ttbar'
evgenConfig.contact = [ "Derrick Allen <derrick.ray.allen@cern.ch>" ]
evgenConfig.keywords += ['SM', 'ttbar']

arrange_output(process_dir=process_dir, runArgs=runArgs)