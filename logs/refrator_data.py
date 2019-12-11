import argparse
import sys
import time

import numpy as np
import pandas as pd



parser = argparse.ArgumentParser(description='Extract Data from Dolphin gamestate and GC actions')

parser.add_argument("--file", type=str, help="path to GC actions", default="logs/keyboard_presses_XXXXXXXXXX.txt")

args = parser.parse_args()

states = pd.read_csv(args.file, header=None)
print(states.shape)
if states.shape[1] == 33:
    ai_states = states.iloc[:,:16]
    opp_states = states.iloc[:,16:-1]
    time = states.iloc[:,-1]

    fox_df = np.empty(time.shape)
    fox_df[:] = 10
    fox_df = pd.DataFrame(data=fox_df)

    stage_df = np.empty(time.shape)
    stage_df[:] = 25
    stage_df = pd.DataFrame(data=stage_df)

    result = pd.concat([stage_df, fox_df, opp_states, fox_df, ai_states, time], axis=1, sort=False)
    print(result.iloc[:, :])
    if result.shape[1] == 36:
        result.to_csv(args.file, index=False, header=None)
    else:
        print("Missing features")
else:
    print("Wrong dim")