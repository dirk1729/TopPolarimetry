"""
Plot all TH1 histograms from hist-L_ttbar.root and hist-R_ttbar.root overlaid.
Outputs one PDF per histogram to Plotting/output/.
"""

import uproot
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep
import os

L_FILE = "MCValidation/run/L_ttbar/hist-L_ttbar.root"
R_FILE = "MCValidation/run/R_ttbar/hist-R_ttbar.root"
OUTPUT_DIR = "Plotting/output"

AXIS_LABELS = {
    "h_top_pt":         ("Top $p_T$ [GeV]",         "Events"),
    "h_top_eta":        ("Top $\\eta$",               "Events"),
    "h_top_phi":        ("Top $\\phi$",               "Events"),
    "h_W_pt":           ("$W$ $p_T$ [GeV]",           "Events"),
    "h_W_eta":          ("$W$ $\\eta$",               "Events"),
    "h_W_phi":          ("$W$ $\\phi$",               "Events"),
    "h_W_child_pt":     ("$W$ child $p_T$ [GeV]",     "Events"),
    "h_W_child_eta":    ("$W$ child $\\eta$",          "Events"),
    "h_W_child_phi":    ("$W$ child $\\phi$",          "Events"),
    "h_W_child_pdgID":  ("$W$ child PDG ID",           "Events"),
    "h_bottom_pt":      ("$b$-quark $p_T$ [GeV]",     "Events"),
    "h_bottom_eta":     ("$b$-quark $\\eta$",          "Events"),
    "h_bottom_phi":     ("$b$-quark $\\phi$",          "Events"),
    "h_cos_theta":      ("$\\cos\\theta^*$",           "Events"),
}


SKIP_HISTS = {"EventLoop_EventCount", "EventLoop_RunTime"}


def get_th1_keys(f):
    """Return names of all TH1 objects in a ROOT file opened with uproot."""
    keys = []
    for name, cls in f.classnames().items():
        base = name.split(";")[0]
        if cls.startswith("TH1") and base not in SKIP_HISTS:
            keys.append(base)
    return keys


def read_hist(f, name):
    """Return (bin_centers, values, errors, edges) for a TH1 in file f."""
    h = f[name]
    values, edges = h.to_numpy()
    errors = np.sqrt(h.variances())
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, values, errors, edges


def plot_hist(name, centers_L, vals_L, errs_L, edges_L,
                    centers_R, vals_R, errs_R, edges_R,
              output_dir):

    hep.style.use("ATLAS")
    fig, ax = plt.subplots(figsize=(7, 5))

    step_L = np.append(vals_L, vals_L[-1])
    step_R = np.append(vals_R, vals_R[-1])

    ax.step(edges_L, step_L, where="post", color="royalblue",  label="L-handed", linewidth=1.8)
    ax.fill_between(edges_L, step_L, step="post", alpha=0.15, color="royalblue")
    ax.errorbar(centers_L, vals_L, yerr=errs_L, fmt="none", color="royalblue", linewidth=1.2)

    ax.step(edges_R, step_R, where="post", color="tomato", label="R-handed", linewidth=1.8)
    ax.fill_between(edges_R, step_R, step="post", alpha=0.15, color="tomato")
    ax.errorbar(centers_R, vals_R, yerr=errs_R, fmt="none", color="tomato", linewidth=1.2)

    xlabel, ylabel = AXIS_LABELS.get(name, (name, "Events"))
    ax.set_xlabel(xlabel, loc="right")
    ax.set_ylabel(ylabel, loc="top")
    ax.set_xlim(edges_L[0], edges_L[-1])
    ax.set_ylim(bottom=0)

    ax.legend(frameon=False)
    hep.atlas.label("Internal", loc=0, ax=ax)

    fig.tight_layout()
    out_path = os.path.join(output_dir, f"{name}.pdf")
    fig.savefig(out_path)
    plt.close(fig)
    print(f"  Saved {out_path}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)

    l_path = os.path.join(repo_root, L_FILE)
    r_path = os.path.join(repo_root, R_FILE)
    out_dir = os.path.join(repo_root, OUTPUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    with uproot.open(l_path) as fL, uproot.open(r_path) as fR:
        keys_L = set(get_th1_keys(fL))
        keys_R = set(get_th1_keys(fR))
        common = sorted(keys_L & keys_R)

        if not common:
            print("No common TH1 histograms found between the two files.")
            return

        print(f"Found {len(common)} histogram(s): {common}\n")

        for name in common:
            centers_L, vals_L, errs_L, edges_L = read_hist(fL, name)
            centers_R, vals_R, errs_R, edges_R = read_hist(fR, name)
            plot_hist(name,
                      centers_L, vals_L, errs_L, edges_L,
                      centers_R, vals_R, errs_R, edges_R,
                      out_dir)

    print(f"\nDone. Plots written to {out_dir}/")


if __name__ == "__main__":
    main()
