import argparse
from decimal import *
from os import listdir
import sys
import time

import numpy as np
import pandas as pd


# parser = argparse.ArgumentParser(description='Extract Data from Dolphin gamestate and GC actions')

# parser.add_argument("--action_file", type=str, help="path to GC actions", default="logs/keyboard_presses_XXXXXXXXXX.txt")
# parser.add_argument("--state_dir", type=str, help="path to states", default="logs/")

# args = parser.parse_args()

# Setup
getcontext().prec = 3
GC_columns = ['A', 'B', 'X', 'Y', 'Z', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'L', 'R', 'ANA:x', 'ANA:y', 'C:x', 'C:y']
GC_headers = {'A':0, 'B':1, 'X':2, 'Y':3, 'Z':4, 'START':5, 'UP':6, 'DOWN':7, 'LEFT':8, 'RIGHT':9, 'L':10, 'R':11, 'ANA':12, 'C':14}
num_headers = 16
precision = 3


def extract_actions(action_file_name):
    if action_file_name[-4:] != '.txt':
        print("Action file is not a txt file")
        sys.exit()

    GC_actions_file = open(action_file_name, 'r')
    GC_actions_data = list()

    for line in GC_actions_file:
        if line[:4] == 'time':
            # time = int(float(line[6:]) * (10 ** precision))
            time = float(line[6:])


        elif line[:2] == 'P1':
            p1 = np.zeros(num_headers)
            p1 = parse_line(line, p1)

        elif line[:2] == 'P2':
            p2 = np.zeros(num_headers)
            p2 = parse_line(line, p2)
            row = np.hstack([time] + [p1] + [p2])
            GC_actions_data.append(row)
    
    return np.vstack(GC_actions_data)

def parse_actions(action_file, num_actions):
    for line in action_file:
        if line[:2] == 'P1':
            p1 = np.zeros(num_actions)
            p1 = parse_line(line, p1)

        elif line[:2] == 'P2':
            p2 = np.zeros(num_actions)
            p2 = parse_line(line, p2)

    row = np.hstack([p1] + [p2])
    return row

def parse_line(line, array):
    line = line.split(' ')
    for elem in line:
        if elem in GC_headers:
            array[GC_headers[elem]] = 1
        else:
            split_values = elem.split(':')
            if elem.split(':')[0] in GC_headers:
                header = elem.split(':')[0]
                split_values = split_values[1].split(',')
                for ii in range(len(split_values)):
                    array[GC_headers[header] + ii] = int(split_values[ii])

    return array


def merge_state_action(actions, states):
    pd.set_option('precision', precision)  
    
    # Actions
    p1_headers = list()
    p2_headers = list()
    for col in GC_columns:
        p1_headers.append("P1" + col)
        p2_headers.append("P2" + col)

    actions = pd.DataFrame(actions[:, 1:], index = actions[:, 0], columns = p1_headers + p2_headers)
    print(actions.index[0])
    print(actions.shape)

    # States
    num_states = states.shape[0]
    time = trunc(np.array(states.iloc[:, -1]), precision)
    states[states.shape[1] - 1] = time
    states = states.set_index(states.shape[1] - 1)
    print(states.index[0])
    print(states.shape)

    # Merge
    result = pd.concat([states, actions], axis=1, join='inner')
    state_actions = result.dropna()
    print(result)
    print(num_states)
    print(state_actions.shape[0])




def find_csvs(path_to_dir, suffix=".csv"):
    filenames = listdir(path_to_dir)
    filenames = [filename for filename in filenames if filename.endswith(suffix)]
    csvs = [pd.read_csv(args.state_dir + filename, header=None) for filename in filenames]
    csvs = pd.concat(csvs, ignore_index=True)
    return csvs


def trunc(values, decs=0):
    return np.trunc(values*10**decs)/(10**decs)


def main():
    GC_actions = extract_actions(args.action_file)
    states = find_csvs(args.state_dir)
    state_action = merge_state_action(GC_actions, states)
    


if __name__ == "__main__":
    main()