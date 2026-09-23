import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score, roc_auc_score
import sys
from new_model import *
from DataLoader_TopCPToolkit import CustomDataset

dir_dataset = str(sys.argv[1])
dir_training = str(sys.argv[2])
model_path = str(sys.argv[3])

batch_size=256

dset = torch.load(dir_dataset+"/dataset_combined.pt", weights_only=False)

generator = torch.Generator().manual_seed(42)

train_dataset, test_dataset = torch.utils.data.random_split(dset, [0.75, 0.25], generator=generator)
val_dataset, test_dataset = torch.utils.data.random_split(test_dataset, [0.2, 0.8], generator=generator)

train_loader = DataLoader(train_dataset, batch_size=batch_size)
val_loader = DataLoader(val_dataset, batch_size=batch_size)
test_loader = DataLoader(test_dataset, batch_size=batch_size)

print("GPU Available: ", torch.cuda.is_available())
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(device)

num_heads=4
model = torch.load(model_path,weights_only=False,map_location=torch.device(device))

def calc_norm(y_pred):
    norm = torch.sqrt(torch.sum(torch.square(y_pred), dim=1)).reshape(-1,1)
    y_pred_norm = torch.div(y_pred, norm)
    return y_pred_norm

direct_feats=1
pred_direct = np.array([]).reshape(0,direct_feats)
true_direct = np.array([]).reshape(0,direct_feats)

for probe_jet, constituents, event, costheta_labels, track_labels in test_loader:
    costheta_pred = model(probe_jet.to(device), constituents.to(device), event.to(device))

    costheta_pred = calc_norm(costheta_pred)

    pred_direct = np.vstack((pred_direct,costheta_pred[:,0].reshape(-1,1).detach().cpu().numpy()))
    true_direct = np.vstack((true_direct,costheta_labels[:,0].reshape(-1,1).detach().cpu().numpy()))

def validate_predictions(true, pred, var_names):
    num_feats = len(var_names)
    ranges_dict = {"costheta": (-1.1,1.1)}

    for i ,var in enumerate(var_names):
        var_range = ranges_dict[var]

        plt.figure()
        plt.hist(np.ravel(true[:,i]),histtype='step',color='r',label='True Distribution',bins=50,range=var_range)
        plt.hist(np.ravel(pred[:,i]),histtype='step',color='b',label='Predicted Distribution',bins=50,range=var_range)
        plt.title("Predicted Ouput Distribution using Attention Model")
        plt.legend()
        plt.yscale('log')
        plt.xlabel(var_names[i],loc='right')
        plt.savefig(dir_training+"/pred_1d_"+var_names[i]+".png")
        #plt.show()
        plt.close()

        #plt.figure()
        fig, ax = plt.subplots()
        plt.title("Ouput Distribution using Attention Model")
        h = ax.hist2d(np.ravel(pred[:,i]),np.ravel(true[:,i]), bins=100,norm=mcolors.LogNorm(),range=(var_range,var_range))
        #fig.colorbar(h[3], ax=ax)
        plt.xlabel('Predicted '+var_names[i],loc='right')
        plt.ylabel('True '+var_names[i],loc='top')
        diff = var_range[1] - var_range[0]
        plt.text(var_range[1]-0.3*diff,var_range[0]+0.2*diff,"$R^2$ value: "+str(round(r2_score(np.ravel(true[:,i]),np.ravel(pred[:,i])),3)),backgroundcolor='r',color='k')
        #print("R^2 value: ", round(r2_score(true_labels[:,i],predicted_labels[:,i]),3))
        plt.savefig(dir_training+"/pred_2d_"+var_names[i]+".png")
        #plt.show()
        plt.close()

validate_predictions(true_direct, pred_direct, ["costheta"])
