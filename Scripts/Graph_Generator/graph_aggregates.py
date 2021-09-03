# Original author: Kevin
# Modified by: Binyamin
# Modified further by : Glenn - 24/03/2021
# And even further by: Eric - Summer/2021

#!/usr/bin/env python
# coding: utf-8

import itertools, threading, time, sys, os, re
import pandas as pd
import matplotlib.pyplot as plt
import shutil
import random

progress = True
log_file_folder = ""

# Handles command line flags
for flag in sys.argv:
    lowered = flag.lower()
    if lowered == "--no-progress" or lowered == "-np":
        progress = False
    elif "-log-dir" in lowered or "-ld" in lowered:
        log_file_folder = flag.split("=",1)[1]

if log_file_folder == "":
    print("\n\033[31mASSERT:\033[m Must set a log folder path using the flag -log-dir=<path to logs folder>\033[0m")
    exit(-1)

# Loading animation
done    = False
success = True
def animate():
    # Loop through the animation cycles
    for c in itertools.cycle(["|", "/", "-", "\\"]):
        # When the global variable is set at the eof
        #  then the infinite loop will break
        if done:
            break
        # Using stdout makes it easier to deal with the newlines inherent in print()
        # '\r' replaces the previous line so we don't crowd the terminal
        sys.stdout.write("\r\033[33maggregating graphs " + c + "\033[0m")
        sys.stdout.flush()
        time.sleep(0.1)
    if success:
        sys.stdout.write("\r\033[1;32mDone.                   \033[0m\n")

# Don't forget to thread it!
if progress:
    t = threading.Thread(target=animate)
    t.start()

# Setup paths, filenames, and folders
log_filename = log_file_folder + "/pandemic_state.txt"
path         = log_file_folder + "/stats/aggregate"
base_name    = path + "/"
shutil.rmtree(path, ignore_errors=True)

# Regex str to find underscore and one or more characters after the underscore (model id)
regex_model_id = "_\w+"
# Regex str to read all state contents between <>
regex_state = "<.+>"

# State log structure
sIndex    = 1
eIndex    = 2
vd1Index  = 3
vd2Index  = 4
iIndex    = 5
rIndex    = 6
neweIndex = 7
newiIndex = 8
newrIndex = 9
dIndex    = 10
bIndex    = 11

COLOR_SUSCEPTIBLE = 'xkcd:blue'
COLOR_INFECTED    = 'xkcd:red'
COLOR_EXPOSED     = 'xkcd:sienna'
COLOR_DOSE1       = '#B91FDE'
COLOR_DOSE2       = '#680D5A'
COLOR_RECOVERED   = 'xkcd:green'
COLOR_DEAD        = 'xkcd:black'
COLOR_BOOSTERS    = {}

line_styles = ['-', '--', '-.', ':']
SOLID    = 0
DASHED   = 1
DOT_DASH = 2
DOTTED   = 3
LINE_BOOSTERS = {}

data        = []
curr_time   = None
curr_states = {}
total_pop   = {}

def curr_states_to_df_row(sim_time, curr_states, total_pop, num_boosters):
    total_S = total_E = total_VD1 = total_VD2 = total_I = total_R = total_D = 0
    new_E = new_I = new_R = total_S
    total_B = {}
    percent_B = {}

    # Sum the number of S,E,V,I,R,D persons in all cells
    for key in curr_states:
        cell_population = curr_states[key][0]
        total_S   += round(cell_population*(curr_states[key][sIndex]))
        total_E   += round(cell_population*(curr_states[key][eIndex]))
        total_VD1 += round(cell_population*(curr_states[key][vd1Index]))
        total_VD2 += round(cell_population*(curr_states[key][vd2Index]))
        total_I   += round(cell_population*(curr_states[key][iIndex]))
        total_R   += round(cell_population*(curr_states[key][rIndex]))
        total_D   += round(cell_population*(curr_states[key][dIndex]))

        for booster in range(0, num_boosters):
            if booster+1 in total_B:
                total_B[booster+1] += round(cell_population*(curr_states[key][bIndex+booster]))
            else:
                total_B[booster+1] = round(cell_population*(curr_states[key][bIndex+booster]))

        new_E += round(cell_population*(curr_states[key][neweIndex]))
        new_I += round(cell_population*(curr_states[key][newiIndex]))
        new_R += round(cell_population*(curr_states[key][newrIndex]))

    # then divide each by the total population to get the percentage of population in each state
    percent_S   = total_S   / total_pop
    percent_E   = total_E   / total_pop
    percent_VD1 = total_VD1 / total_pop
    percent_VD2 = total_VD2 / total_pop
    percent_I   = total_I   / total_pop
    percent_R   = total_R   / total_pop
    percent_D   = total_D   / total_pop

    for booster in range(0, num_boosters):
        percent_B[booster+1] = total_B[booster+1] / total_pop

    percent_new_E = new_E / total_pop
    percent_new_I = new_I / total_pop
    percent_new_R = new_R / total_pop
    psum = percent_S + percent_E + percent_VD1 + percent_VD2 + percent_I + percent_R + percent_D

    assert 0.95 <= psum < 1.05, ("at time " + str(curr_time))

    array = [int(sim_time), percent_S, percent_E, percent_VD1, percent_VD2, percent_I, percent_R, percent_new_E, percent_new_I, percent_new_R, percent_D]
    for booster in range(0, num_boosters):
        array.append(percent_B[booster+1])
    array.append(psum)
    return array

try:
    if __name__ == "__main__":
        num_boosters = -1

        # Read the data of all regions and their names
        with open(log_filename, "r") as log_file:
            # Read the file twice
            #   Once to get the total_pop
            #   A second time to calculate the data
            for i in range(2):
                log_file.seek(0, 0)
                line_num = 0

                # For each line, read a line then:
                for line in log_file:
                    # Strip leading and trailing spaces
                    line = line.strip()

                    # If a time marker is found that is not the current time
                    if line.isnumeric() and line != curr_time:
                        if curr_states and i == 1:
                            if num_boosters == -1:
                                num_boosters = 0
                                try:
                                    while True:
                                        list(curr_states.values())[0][bIndex+num_boosters]
                                        num_boosters += 1
                                except Exception:
                                    pass

                            data.append(curr_states_to_df_row(curr_time, curr_states, sum(list(total_pop.values())), num_boosters))

                        # Update new simulation time
                        curr_time = line
                        continue

                    # Create an re match objects from the current line
                    state_match = re.search(regex_state,line)
                    id_match    = re.search(regex_model_id,line)
                    if not (state_match and id_match):
                        continue

                    # Parse the state and id and insert into total_pop
                    cid     = id_match.group().lstrip('_')
                    state   = state_match.group().strip('<>')
                    state   = state.split(',')

                    if i == 0:
                        total_pop[cid] = float(state[0])
                    elif i == 1:
                        state = list(map(float, state))
                        curr_states[cid] = state

                    line_num += 1

            data.append(curr_states_to_df_row(curr_time, curr_states, sum(total_pop.values()), num_boosters))

        try:
            os.makedirs(path)
        except OSError as error:
            raise error

        with open(base_name+"aggregate_timeseries.csv", 'w') as out_file:
            out_str = "sim_time, S, E, VD1, VD2, I, R, New_E, New_I, New_R, D"
            for booster in range(0, num_boosters):
                out_str += ", booster" + str(booster+1)
            out_str += ", pop_sum\n"
            out_file.write(out_str)
            for timestep in data:
                out_file.write(str(timestep).strip('[]')+"\n")

        columns = ["time", "susceptible", "exposed", "vaccinatedD1", "vaccinatedD2", "infected",
                    "recovered", "new_exposed", "new_infected", "new_recovered", "deaths"]
        for booster in range(0, num_boosters):
            columns.append("booster"+str(booster+1))
            COLOR_BOOSTERS[booster] = "#%06x" % random.randint(0, 0xFFFFFF)
            LINE_BOOSTERS[booster]  = random.choice(line_styles)
        columns.append("error")
        df_vis = pd.DataFrame(data, columns=columns)
        df_vis = df_vis.set_index("time")
        df_vis.to_csv(log_file_folder+"/states.csv")
        df_vis.head()
        x = list(df_vis.index)

        ### --- New EIR --- ###
        fig, ax = plt.subplots(figsize=(15,6))

        ax.plot(x, 100*df_vis["new_exposed"],   label="New exposed",   color=COLOR_EXPOSED,   linestyle=line_styles[DOT_DASH])
        ax.plot(x, 100*df_vis["new_infected"],  label="New infected",  color=COLOR_INFECTED,  linestyle=line_styles[DASHED])
        ax.plot(x, 100*df_vis["new_recovered"], label="New recovered", color=COLOR_RECOVERED, linestyle=line_styles[DOTTED])
        plt.legend(loc="upper right")
        plt.title("Epidemic Aggregate New EIR Percentages")
        plt.xlabel("Time (days)")
        plt.ylabel("Population (%)")
        plt.savefig(base_name + "New_EIR.png")

        ### --- SEIRD/SEVIRD --- ###
        fig, ax = plt.subplots(figsize=(15,6))

        ax.plot(x, 100*df_vis["susceptible"], label="Susceptible", color=COLOR_SUSCEPTIBLE, linestyle=line_styles[SOLID])
        if not (sum(df_vis['vaccinatedD1']) == 0 and sum(df_vis['vaccinatedD2']) == 0):
            ax.plot(x, 100*df_vis["vaccinatedD1"], label="Vaccinated 1 Dose",  color=COLOR_DOSE1, linestyle=line_styles[SOLID])
            ax.plot(x, 100*df_vis["vaccinatedD2"], label="Vaccinated 2 Doses", color=COLOR_DOSE2, linestyle=line_styles[DASHED])
            for booster in range(0, num_boosters):
                ax.plot(x, 100*df_vis["booster"+str(booster+1)], label="Booster "+str(booster+1),
                        color=COLOR_BOOSTERS[booster],
                        linestyle=LINE_BOOSTERS[booster])
            plt.title("Epidemic Aggregate SEVIRD Percentages")
        else:
            plt.title("Epidemic Aggregate SEIR+D Percentages")

        ax.plot(x, 100*df_vis["exposed"],   label="Exposed",   color=COLOR_EXPOSED,   linestyle=line_styles[DOT_DASH])
        ax.plot(x, 100*df_vis["infected"],  label="Infected",  color=COLOR_INFECTED,  linestyle=line_styles[DASHED])
        ax.plot(x, 100*df_vis["recovered"], label="Recovered", color=COLOR_RECOVERED, linestyle=line_styles[DOTTED])
        plt.ylabel("Population (%)")
        plt.xlabel("Time (days)")
        plt.legend(loc="upper right")

        if not (sum(df_vis['vaccinatedD1']) == 0 and sum(df_vis['vaccinatedD2']) == 0):
            plt.savefig(base_name + "SEVIRD.png")
        else:
            plt.savefig(base_name + "SEIR+D.png")
        plt.close(fig)

        ### --- EID --- ###
        fig, ax = plt.subplots(figsize=(15, 6))

        ax.plot(x, 100*df_vis["deaths"],   label="Deaths",
                color=COLOR_DEAD,     linestyle=line_styles[SOLID])
        ax.plot(x, 100*df_vis["exposed"],  label="Exposed",
                color=COLOR_EXPOSED,  linestyle=line_styles[DOT_DASH])
        ax.plot(x, 100*df_vis["infected"], label="Infected",
                color=COLOR_INFECTED, linestyle=line_styles[DASHED])
        plt.title("Epidemic Aggregate EID Percentages")
        plt.xlabel("Time (days)")
        plt.ylabel("Population (%)")
        plt.legend(loc="upper right")
        plt.savefig(base_name + "EID.png")

        fig, ax = plt.subplots(figsize=(15, 6))
        if not (sum(df_vis['vaccinatedD1']) == 0 and sum(df_vis['vaccinatedD2']) == 0) and num_boosters > 0:
            ax.plot(x, 100*df_vis["vaccinatedD1"], label="Vaccinated 1 Dose",  color=COLOR_DOSE1, linestyle=line_styles[SOLID])
            ax.plot(x, 100*df_vis["vaccinatedD2"], label="Vaccinated 2 Doses", color=COLOR_DOSE2, linestyle=line_styles[DASHED])
            for booster in range(0, num_boosters):
                ax.plot(x, 100*df_vis["booster"+str(booster+1)], label="Booster "+str(booster+1),
                        color=COLOR_BOOSTERS[booster],
                        linestyle=LINE_BOOSTERS[booster])
            plt.title("Epidemic Aggregate Vaccine Percentages")
            plt.ylabel("Population (%)")
            plt.xlabel("Time (days)")
            plt.legend(loc="upper right")
            plt.savefig(base_name + "Vaccines.png")

        if not progress:
            print("\033[1;32mDone.\033[0m")
        else:
            done = True
            t.join()
    #if
except AssertionError as assertion:
    success = False
    done = True
    if progress:
        t.join()

    print("\n\033[31mASSERT:\033[0m 0.995 <= psum < 1.005", assertion)
    sys.exit(-1)
except KeyboardInterrupt as interrupt:
    success = False
    done = True
    if progress:
        t.join()

    print("\n\033[33mStopped by user\033[0m")
    sys.exit(-1)
# except Exception as error:
#     success = False
#     done = True
#     if progress:
#         t.join()

#     print("\n\033[31m" + str(error) + "\033[0m")
