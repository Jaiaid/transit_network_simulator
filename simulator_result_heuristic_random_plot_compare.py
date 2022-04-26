import numpy as np
import os
import re
import sys
import matplotlib.pyplot as plot

MINIMUM_EVACUEE = 20000
HEU_RESULT_ROOT_DIR = "output/without_reroute_20220105"
RANDOM_RESULT_ROOT_DIR = "halifax_exp_random_route_20220107_result_1_56_customsim_random_gen_route_simulator_nonreroute_output"
RANDOM_SOLUTION_REPEAT = 5

# data structure to contain parsed metric associated with result filename
simulator_random_resultfile_maxhop_result_dict = {}
simulator_heu_resultfile_maxhop_result_dict = {}


def parse_data(result_dir: str, result_dict: dict):
    # file parse related regex
    REGEX_WAITTIME = r"^Waiting time: (\d*\.\d+)"
    REGEX_EVACTIME = r"^Total Evacuation Time: (\d*\.\d+)"
    REGEX_TRIPCOUNT = r"^Number of trips: (\d+)"
    REGEX_EVACUEECOUNT = r"^Number of evacuaees: (\d+)"
    REGEX_RESULT_FILENAME = r"result(\d+).txt"

    # data structure to contain parsed metric from file
    list_waiting_time = []
    list_trip_count = []
    list_evacuation_time = []
    list_evacuaee = []
    list_filename = []

    total_parsed_file = 0
    for i, filename in enumerate(os.listdir(result_dir)):
        # file should of type text and with prefix "result"
        basename = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1]

        if extension != ".txt" or not basename.startswith("result"):
            continue

        hopcount = int(re.search(REGEX_RESULT_FILENAME, filename).groups()[0])
        if hopcount not in result_dict:
            result_dict[hopcount] = [[], [], [], []]
 
        evac_time = None
        wait_time = None
        trip_count = None
        evacuee_count = None

        filepath = os.path.join(result_dir, filename)
        with open(filepath) as fin:
            for logline in fin.readlines():
                result = re.search(REGEX_EVACTIME, logline)
                if result is not None:
                    evac_time = float(result.groups()[0])
                    continue
                result = re.search(REGEX_WAITTIME, logline)
                if result is not None:
                    wait_time = float(result.groups()[0])
                    continue
                result = re.search(REGEX_TRIPCOUNT, logline)
                if result is not None:
                    trip_count = int(result.groups()[0])
                    continue
                result = re.search(REGEX_EVACUEECOUNT, logline)
                if result is not None:
                    evacuee_count = int(result.groups()[0])
                    continue

        if evacuee_count >= MINIMUM_EVACUEE:
            if evac_time is not None:
                result_dict[hopcount][0].append(evac_time)
                list_evacuation_time.append(evac_time)

            if wait_time is not None:
                result_dict[hopcount][1].append(wait_time)
                list_waiting_time.append(wait_time)

            if trip_count is not None:
                result_dict[hopcount][2].append(trip_count)
                list_trip_count.append(trip_count)

            result_dict[hopcount][3].append(evacuee_count)
            list_evacuaee.append(evacuee_count)
            list_filename.append(filename)

            
        total_parsed_file += 1

    # check sanity of data parsing
    # if parsing is correct parsed file count should be equal to data point count for each metrics
    try:
        assert len(list_evacuation_time) == len(list_trip_count) == len(list_waiting_time) == total_parsed_file
    except AssertionError as e:
        print("""
            mismatch in data point count and parsed file count 
            total file : {0} 
            tripcount data point count : {1} 
            evactime data point count : {2} 
            waittime data point count : {3}
            for dir : {4}
            """.format(total_parsed_file, len(list_trip_count), len(list_evacuation_time), len(list_waiting_time), result_dir))


def draw_plot(ax0, ax1, ax2, result_dict, label_list):
    x0 = []
    x1 = []
    x2 = []
    y0 = []
    y1 = []
    y2 = []
    
    for key in sorted(list(result_dict.keys())):
        if len(result_dict[key][0]) > 0:
            x0.append(key)
            y0.append(sum(result_dict[key][0])/len(result_dict[key][0]))
        if len(result_dict[key][1]) > 0:
            x1.append(key)
            y1.append(sum(result_dict[key][1])/len(result_dict[key][1]))
        if len(result_dict[key][2]) > 0:
            x2.append(key)
            y2.append(sum(result_dict[key][2])/len(result_dict[key][2]))

    ax0.plot(x0, y0, label=label_list[0])
    ax1.plot(x1, y1, label=label_list[1])
    ax2.plot(x2, y2, label=label_list[2])


if __name__=="__main__":
    # first extract the information from result corresponding to random generated routeset 
    for solution_no in range(1, RANDOM_SOLUTION_REPEAT+1):
        input_dir = os.path.join(RANDOM_RESULT_ROOT_DIR, "solution_{0}".format(solution_no))
        solutionno_result_dir = os.path.join(RANDOM_RESULT_ROOT_DIR, "solution_{0}".format(solution_no))

        # parse the newly created directory files to get stat
        parse_data(solutionno_result_dir, simulator_random_resultfile_maxhop_result_dict)

    # extract the information from result corresponding to heuristic generated routeset 
    parse_data(HEU_RESULT_ROOT_DIR, simulator_heu_resultfile_maxhop_result_dict)

    fig_evac, ax_evac = plot.subplots()
    fig_wait, ax_wait = plot.subplots()
    fig_trip, ax_trip = plot.subplots()
    
    draw_plot(ax_evac, ax_wait, ax_trip, simulator_heu_resultfile_maxhop_result_dict, ["rand sol evac time", "rand sol wait time", "rand sol trip count"])
    draw_plot(ax_evac, ax_wait, ax_trip, simulator_random_resultfile_maxhop_result_dict, ["heu evac time", "heu wait time", "heu trip count"])

    ax_evac.set_title("Evacuation Time Compare")
    ax_evac.legend()
    ax_evac.set_xlabel("max pickup point")
    ax_evac.set_ylabel("evac time(hour)")
    #ax_evac.xaxis.set_tick_params(labelsize="4")
    fig_evac.savefig("heuristic_vs_random_generation_evactime_compare.png", dpi=300)
    
    ax_wait.set_title("Waiting Time Compare")
    ax_wait.legend()
    ax_wait.set_xlabel("max pickup point")
    ax_wait.set_ylabel("wait time(second)")
    fig_wait.savefig("heuristic_vs_random_generation_waittime_compare.png", dpi=300)

    ax_trip.set_title("Trip Count Compare")
    ax_trip.legend()
    ax_trip.set_xlabel("max pickup point")
    ax_trip.set_ylabel("trip count")
    fig_trip.savefig("heuristic_vs_random_generation_tripcount_compare.png", dpi=300)
