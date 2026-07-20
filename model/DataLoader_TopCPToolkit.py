import uproot
import awkward as ak
import numpy as np
import torch
from torch.utils.data import Dataset
import torch.multiprocessing
torch.multiprocessing.set_sharing_strategy('file_system')
import sys

from DataLoader_Parallel import sort_by_pT, clip_to_num, combine_feats

# Loads reco-level ntuples produced by TopCPToolkit/TopPolarimetry (see
# source/TopPolarimetry/share/configs/mc/reco.yaml), instead of the Pythia
# truth-level "fastjet" ntuples DataLoader_Parallel.py was built for.
#
# Two structural differences from the old pipeline, driven by what's actually
# available in this reco tree:
#
#  - Jets here are resolved AntiKt4EMPFlowJets (R=0.4), not one large merged
#    jet holding the whole hadronic top decay. So "probe jet" = the single
#    jet matched to the down-type quark (jet_idx_down_from_thad), which is
#    the spin-analyzing object; "balance jets" = every other jet in the event.
#    Its ghost-associated ID tracks (jet_constituent_trk_*, from
#    TopPolJetConstituentsAlg) stand in for the old probe_jet_constituent_*
#    branches, with fromDown/fromUp/fromBottom labeled at jet granularity
#    (see that algorithm's docstring for why: true track-level truth
#    ancestry isn't recoverable from this DAOD_PHYS sample).
#
#  - top/down/bottom boosted-frame kinematic labels aren't in this tree at
#    all (they were computed directly from Pythia truth in the old
#    pipeline); only the polarimetric angle is, precomputed as
#    spin_MySpin_cos_theta_helicity_{p,m}_NOSYS. p/m are the top/antitop
#    sides respectively, so t_isHadronic picks out the side whose jets we're
#    actually using as inputs. Reconstructing top/down/bottom labels would
#    need cross-matching to the particleLevel truth tree (by event number),
#    which this loader does not attempt.
class CustomDataset(Dataset):
    def __init__(self, file):
        probe_jet_feats, probe_jet_constituent_feats, event_tensor_feats, costheta_labels, track_labels = \
            load_file(file)

        self.probe_jet = probe_jet_feats
        self.probe_jet_constituents = probe_jet_constituent_feats
        self.event_tensor_feats = event_tensor_feats
        self.costheta_labels = costheta_labels
        self.track_labels = track_labels

    def __getitem__(self, idx):
        return (self.probe_jet[idx], self.probe_jet_constituents[idx], self.event_tensor_feats[idx],
                self.costheta_labels[idx], self.track_labels[idx])

    def __len__(self):
        return len(self.probe_jet)


def compute_jet_mass(pt, eta, phi, e):
    px = pt * np.cos(phi)
    py = pt * np.sin(phi)
    pz = pt * np.sinh(eta)
    m2 = e**2 - (px**2 + py**2 + pz**2)
    return np.sqrt(ak.where(m2 > 0, m2, 0.0))


def load_file(file):
    print(file)
    with uproot.open(file)["reco"] as tree:
        jet_pt = tree["jet_pt_NOSYS"].array()
        jet_eta = tree["jet_eta"].array()
        jet_phi = tree["jet_phi"].array()
        jet_e = tree["jet_e_NOSYS"].array()
        jet_idx_down_from_thad = tree["jet_idx_down_from_thad"].array()

        trk_pt = tree["jet_constituent_trk_pt"].array()
        trk_eta = tree["jet_constituent_trk_eta"].array()
        trk_phi = tree["jet_constituent_trk_phi"].array()
        trk_q = tree["jet_constituent_trk_q"].array()
        trk_fromDown = tree["jet_constituent_trk_fromDown"].array()
        trk_fromUp = tree["jet_constituent_trk_fromUp"].array()
        trk_fromBottom = tree["jet_constituent_trk_fromBottom"].array()

        el_pt = tree["el_pt_NOSYS"].array()
        el_eta = tree["el_eta"].array()
        el_phi = tree["el_phi"].array()
        el_q = tree["el_charge"].array()
        mu_pt = tree["mu_pt_NOSYS"].array()
        mu_eta = tree["mu_eta"].array()
        mu_phi = tree["mu_phi"].array()
        mu_q = tree["mu_charge"].array()

        met = tree["met_met_NOSYS"].array()
        met_phi = tree["met_phi_NOSYS"].array()

        cos_theta_helicity_p = tree["spin_MySpin_cos_theta_helicity_p_NOSYS"].array()
        cos_theta_helicity_m = tree["spin_MySpin_cos_theta_helicity_m_NOSYS"].array()
        t_isHadronic = tree["t_isHadronic"].array()

        pass_lepjets = tree["pass_lepjets_LooseLH_NOSYS"].array()

    # keep only events with a valid lepton+jets selection and a matched probe jet
    keep = (pass_lepjets == 1) & (jet_idx_down_from_thad >= 0)

    jet_pt, jet_eta, jet_phi, jet_e = jet_pt[keep], jet_eta[keep], jet_phi[keep], jet_e[keep]
    jet_idx_down_from_thad = jet_idx_down_from_thad[keep]
    trk_pt, trk_eta, trk_phi, trk_q = trk_pt[keep], trk_eta[keep], trk_phi[keep], trk_q[keep]
    trk_fromDown, trk_fromUp, trk_fromBottom = trk_fromDown[keep], trk_fromUp[keep], trk_fromBottom[keep]
    el_pt, el_eta, el_phi, el_q = el_pt[keep], el_eta[keep], el_phi[keep], el_q[keep]
    mu_pt, mu_eta, mu_phi, mu_q = mu_pt[keep], mu_eta[keep], mu_phi[keep], mu_q[keep]
    met, met_phi = met[keep], met_phi[keep]
    cos_theta_helicity_p, cos_theta_helicity_m = cos_theta_helicity_p[keep], cos_theta_helicity_m[keep]
    t_isHadronic = t_isHadronic[keep]

    jet_mass = compute_jet_mass(jet_pt, jet_eta, jet_phi, jet_e)

    # select the probe jet (down-type-quark-matched) per event
    probe_mask = ak.local_index(jet_pt) == jet_idx_down_from_thad

    probe_jet_dict = {
        "pT": ak.firsts(jet_pt[probe_mask]),
        "eta": ak.firsts(jet_eta[probe_mask]),
        "phi": ak.firsts(jet_phi[probe_mask]),
        "mass": ak.firsts(jet_mass[probe_mask]),
    }

    probe_jet_constituent_dict = {
        "pT": ak.firsts(trk_pt[probe_mask], axis=1),
        "eta": ak.firsts(trk_eta[probe_mask], axis=1),
        "phi": ak.firsts(trk_phi[probe_mask], axis=1),
        "q": ak.firsts(trk_q[probe_mask], axis=1),
        "fromDown": ak.firsts(trk_fromDown[probe_mask], axis=1),
        "fromUp": ak.firsts(trk_fromUp[probe_mask], axis=1),
        "fromBottom": ak.firsts(trk_fromBottom[probe_mask], axis=1),
    }

    balance_jet_dict = {
        "pT": jet_pt[~probe_mask],
        "eta": jet_eta[~probe_mask],
        "phi": jet_phi[~probe_mask],
    }

    max_constituent_num = 200
    max_balance_jet_num = 10

    sorted_probe_jet_constituent_dict = sort_by_pT(probe_jet_constituent_dict)
    clipped_probe_jet_constituent_dict = clip_to_num(sorted_probe_jet_constituent_dict, max_constituent_num, axis=1)

    sorted_balance_jet_dict = sort_by_pT(balance_jet_dict)
    clipped_balance_jet_dict = clip_to_num(sorted_balance_jet_dict, max_balance_jet_num, axis=1)

    # exactly one lepton is expected per selected event; take whichever
    # collection (electron or muon) is non-empty
    has_el = ak.num(el_pt) > 0
    lepton_dict = {
        "pT": ak.where(has_el, ak.firsts(el_pt), ak.firsts(mu_pt)),
        "eta": ak.where(has_el, ak.firsts(el_eta), ak.firsts(mu_eta)),
        "phi": ak.where(has_el, ak.firsts(el_phi), ak.firsts(mu_phi)),
        "q": ak.where(has_el, ak.firsts(el_q), ak.firsts(mu_q)),
    }

    # Combine feats
    probe_jet_feats = combine_feats([probe_jet_dict["pT"], probe_jet_dict["eta"],
                                     probe_jet_dict["phi"], probe_jet_dict["mass"]], axis=1)
    probe_jet_constituent_feats = combine_feats(
        [clipped_probe_jet_constituent_dict["pT"], clipped_probe_jet_constituent_dict["eta"],
         clipped_probe_jet_constituent_dict["phi"], clipped_probe_jet_constituent_dict["q"]], axis=2)
    lepton_feats = combine_feats([lepton_dict["pT"], lepton_dict["eta"],
                                  lepton_dict["phi"], lepton_dict["q"]], axis=1)
    MET_feats = combine_feats([met, met_phi], axis=1)
    balance_jets_feats = combine_feats(
        [clipped_balance_jet_dict["pT"], clipped_balance_jet_dict["eta"],
         clipped_balance_jet_dict["phi"]], axis=2)

    # Pad feats to common length
    common_feat_len = 4
    probe_jet_feats = ak.fill_none(ak.pad_none(probe_jet_feats, common_feat_len, axis=1), 0)
    probe_jet_constituent_feats = ak.fill_none(ak.pad_none(probe_jet_constituent_feats, common_feat_len, axis=2), 0)
    lepton_feats = ak.fill_none(ak.pad_none(lepton_feats, common_feat_len, axis=1), 0)
    MET_feats = ak.fill_none(ak.pad_none(MET_feats, common_feat_len, axis=1), 0)
    balance_jets_feats = ak.fill_none(ak.pad_none(balance_jets_feats, common_feat_len, axis=2), 0)

    # Labels: helicity-basis polarimetric angle for whichever top decayed hadronically
    costheta = ak.where(t_isHadronic, cos_theta_helicity_p, cos_theta_helicity_m)
    costheta_labels = combine_feats([costheta], axis=1)
    track_labels = combine_feats([clipped_probe_jet_constituent_dict["fromDown"],
                                  clipped_probe_jet_constituent_dict["fromUp"],
                                  clipped_probe_jet_constituent_dict["fromBottom"]], axis=2)

    # Convert to tensors
    probe_jet_feats = torch.unsqueeze(torch.tensor(probe_jet_feats, dtype=torch.float32), 1)
    probe_jet_constituent_feats = torch.tensor(probe_jet_constituent_feats, dtype=torch.float32)
    lepton_feats = torch.unsqueeze(torch.tensor(lepton_feats, dtype=torch.float32), 1)
    MET_feats = torch.unsqueeze(torch.tensor(MET_feats, dtype=torch.float32), 1)
    balance_jets_feats = torch.tensor(balance_jets_feats, dtype=torch.float32)

    event_tensor_feats = torch.cat([probe_jet_feats, probe_jet_constituent_feats, lepton_feats,
                                    MET_feats, balance_jets_feats], dim=1)

    return probe_jet_feats, probe_jet_constituent_feats, event_tensor_feats, costheta_labels, track_labels


if __name__ == "__main__":
    in_file = str(sys.argv[1])
    out_file = str(sys.argv[2])

    dset = CustomDataset(in_file)
    torch.save(dset, out_file)
