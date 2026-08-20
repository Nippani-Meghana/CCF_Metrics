#data_loading.py

#Importing necessary libraries
import json
import os
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle



from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def _resolve_path(*parts):
    return str((PROJECT_ROOT / Path(*parts)).resolve())

h5_file_path_gt = _resolve_path("output", "xor", "GT_h5", "groundtruth.h5")
h5_file_path_sub = _resolve_path("output", "xor", "sub_h5", "submission.h5")

# Loading GT and SUB Data
def get_data():
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "output"
    # Output/GT_h5/groundtruth.h5
    h5_file_path_gt = str(output_dir / "xor" / "GT_h5" / "groundtruth.h5")
    gt_data = pd.read_hdf(h5_file_path_gt, "/data")
    print("GT Voltage Data Loading done!")
    gt_spikes = pd.read_hdf(h5_file_path_gt, "/spikes_raw")
    print("GT Spikes Data Loading done!")

    h5_file_path_sub = str(output_dir / "xor" / "SUB_h5" / "sub.h5")
    sub_data = pd.read_hdf(h5_file_path_sub, "/data")
    print("SUB Voltage Data Loading done!")
    sub_spikes = pd.read_hdf(h5_file_path_sub, "/spikes_raw")
    print("SUB Spikes Data Loading done!")

    # Common to both GT and SUB
    cfg = pd.read_hdf(h5_file_path_gt, "/network_config")
    print("Network configuration Loading done!")
    tmap = pd.read_hdf(h5_file_path_gt, "/trial_map")
    print("Trial Map Loading done!")

    with open(output_dir / "xor" / "GT" / "network_config.json", "r") as f:
        net_config = json.load(f)
    truth_table = net_config["truth_table"]

    return gt_data, gt_spikes, sub_data, sub_spikes, cfg, tmap, truth_table, h5_file_path_gt, h5_file_path_sub

get_data()
print("Data Loading done!")