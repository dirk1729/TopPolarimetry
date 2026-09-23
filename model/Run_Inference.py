import torch
from torch.utils.data import DataLoader
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

from DataLoader_TopCPToolkit import CustomDataset

# Runs a trained model on every event in a dataset (no train/val/test split) --
# for scoring a held-out sample the model was never trained/validated on.
dataset_path = str(sys.argv[1])
model_path = str(sys.argv[2])
out_dir = str(sys.argv[3]) if len(sys.argv) > 3 else (os.path.dirname(dataset_path) or ".")

batch_size = 256

dset = torch.load(dataset_path, weights_only=False)
loader = DataLoader(dset, batch_size=batch_size)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model = torch.load(model_path, weights_only=False, map_location=device)
model.eval()

def calc_norm(y_pred):
    norm = torch.sqrt(torch.sum(torch.square(y_pred), dim=1)).reshape(-1, 1)
    return torch.div(y_pred, norm)

pred_costheta = np.array([])
true_costheta = np.array([])

with torch.no_grad():
    for probe_jet, constituents, event, costheta_labels, track_labels in loader:
        costheta_pred = model(probe_jet.to(device), constituents.to(device), event.to(device))
        costheta_pred = calc_norm(costheta_pred)

        pred_costheta = np.concatenate((pred_costheta, costheta_pred[:, 0].detach().cpu().numpy()))
        true_costheta = np.concatenate((true_costheta, costheta_labels[:, 0].detach().cpu().numpy()))

print(f"Events: {len(pred_costheta)}")
for i in range(len(pred_costheta)):
    print(f"  event {i}: true costheta = {true_costheta[i]:+.4f}   predicted costheta = {pred_costheta[i]:+.4f}")

if len(pred_costheta) > 1:
    from sklearn.metrics import r2_score
    r2 = r2_score(true_costheta, pred_costheta)
    print(f"\nR^2: {r2:.4f}")
    print(f"Mean true costheta: {true_costheta.mean():+.4f}")
    print(f"Mean predicted costheta: {pred_costheta.mean():+.4f}")

    os.makedirs(out_dir, exist_ok=True)
    costheta_range = (-1.1, 1.1)

    # 1D: true vs predicted costheta distributions
    plt.figure()
    plt.hist(true_costheta, histtype='step', color='r', label='True Distribution', bins=50, range=costheta_range)
    plt.hist(pred_costheta, histtype='step', color='b', label='Predicted Distribution', bins=50, range=costheta_range)
    plt.title("Predicted Output Distribution using Attention Model")
    plt.legend()
    plt.yscale('log')
    plt.xlabel('costheta', loc='right')
    plt.savefig(out_dir + "/inference_1d_costheta.png")
    plt.close()

    # 2D: predicted vs true costheta, per event. A scatter (not New_Eval.py's
    # hist2d) since inference sets are often too small for 100 bins to be
    # meaningful.
    plt.figure()
    plt.scatter(pred_costheta, true_costheta, s=10, alpha=0.6)
    plt.plot(costheta_range, costheta_range, 'k--', linewidth=1, label='y = x')
    plt.title("Predicted vs True costheta")
    plt.xlabel('Predicted costheta', loc='right')
    plt.ylabel('True costheta', loc='top')
    plt.xlim(costheta_range)
    plt.ylim(costheta_range)
    diff = costheta_range[1] - costheta_range[0]
    plt.text(costheta_range[1] - 0.5 * diff, costheta_range[0] + 0.1 * diff,
              "$R^2$ value: " + str(round(r2, 3)), backgroundcolor='r', color='k')
    plt.legend(loc='upper left')
    plt.savefig(out_dir + "/inference_2d_costheta.png")
    plt.close()

    print(f"\nPlots saved to {out_dir}/inference_1d_costheta.png and {out_dir}/inference_2d_costheta.png")
