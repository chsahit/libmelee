import argparse
from os import listdir
import sys
import time

import math
import numpy as np
import pandas as pd


# Setup
GC_columns = ['A', 'B', 'X', 'Y', 'Z', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'L', 'R', 'ANA:x', 'ANA:y', 'C:x', 'C:y']
GC_headers = {'A':0, 'B':1, 'X':2, 'Y':3, 'Z':4, 'START':5, 'UP':6, 'DOWN':7, 'LEFT':8, 'RIGHT':9, 'L':10, 'R':11, 'ANA':12, 'C':14}
num_headers = 16
precision = 3


# EXTRACT Actions
def extract_actions(action_file_name):
    if action_file_name[-4:] != '.txt':
        print("Action file is not a txt file")
        sys.exit()
    if 'logs/' in action_file_name:
        path = action_file_name
    else:
        path = 'logs/' + action_file_name
    with open(path, 'r') as action_file:
        return parse_actions(action_file.read().splitlines(), num_headers)


def parse_actions(actions_data, num_actions):
    actions = list()
    time = None
    p1 = None
    p2 = None
    for line in actions_data:
        if line[:4] == 'time':
            # time = int(float(line[6:]) * (10 ** precision))
            print(line[6:])
            time = float(line[6:])

        elif line[:2] == 'P1':
            p1 = np.zeros(num_actions)
            p1 = parse_line(line, p1)

        elif line[:2] == 'P2':
            p2 = np.zeros(num_actions)
            p2 = parse_line(line, p2)

            if time != None and p1 is not None and p2 is not None:
                row = np.hstack([time] + [p1] + [p2])
                actions.append(row)
            else:
                print("An action is lost")

            time = None
            p1 = None
            p2 = None

    return np.vstack(actions)

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
                    if split_values[ii].isdigit():
                        array[GC_headers[header] + ii] = int(split_values[ii])
                    else:
                        array[GC_headers[header] + ii] = 0

    return array


# Extract STATES
def find_csvs(file_path, num_states=32):
    states = np.array(pd.read_csv(file_path, header=None))
    states = states[:, :num_states]
    return states


# MERGE
def merge_state_action(states, actions):
    pd.set_option('precision', precision)

    # Actions
    actions = np.array(actions)
    print(actions.shape)

    # States
    states = np.array(states)
    num_states = states.shape[0]

    # Merge
    state_indexes= list()
    action_indexes = list()
    action_times = actions[:, 0]
    action_idx = 0
    for ii in range(states.shape[0]):

        value = states[ii, 0]
        idx = find_nearest(action_times[action_idx:], value, threshold=0.01)

        if idx > -1:
            state_indexes.append(ii)
            action_indexes.append(idx + action_idx)
            action_idx = idx

    state_actions = np.hstack([states[state_indexes], actions[action_indexes]])
    print(state_actions.shape)
    print("Number of states lost - " + str(num_states - state_actions.shape[0]))
    return state_actions


# Helpers
def trunc(values, decs=0):
    return np.trunc(values*10**decs)/(10**decs)


def find_nearest(array, value, threshold=0.01):
    idx = np.searchsorted(array, value, side="left")

    if idx > 0 and idx < len(array):
        diff_1 = math.fabs(value - array[idx-1])
        diff_2 = math.fabs(value - array[idx])
        if diff_1 > threshold and diff_2 > threshold:
            return -1

        if diff_1 < diff_2:
            return idx - 1
        else:
            return idx
    else:
        return -1


# Main
def main(args):
    GC_actions = extract_actions(args.action_file)
    states = find_csvs(args.state_file)
    state_action = merge_state_action(states, GC_actions)

    if (state_action.shape[0] / states.shape[0]) < .9:
        print("Not Saving, Too many lost states")
        sys.exit()
    else:
        if args.test:
            np.savetxt("logs/examples.csv", state_action, delimiter=",")
        else:
            np.savetxt(args.state_file, state_action, delimiter=",")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract Data from Dolphin gamestate and GC actions')

    parser.add_argument("--action_file", type=str, help="path to GC actions", default="logs/keyboard_presses_XXXXXXXXXX.txt")
    parser.add_argument("--state_file", type=str, help="path to states", default="logs/gameX_XXXXXXXXXX.csv")
    parser.add_argument('--test', '-t', default=False, action='store_true')

    args = parser.parse_args()
    main(args)
