import numpy as np
import os
import re
import sys

MINIMUM_EVACUEE = 62858

def parse_data(result_dir: str):
    # file parse related regex
    REGEX_WAITTIME = r"^Waiting time: (\d*\.\d+)"
    REGEX_EVACTIME = r"^Total Evacuation Time: (\d*\.\d+)"
    REGEX_TRIPCOUNT = r"^Number of trips: (\d+)"
    REGEX_EVACUEECOUNT = r"^Number of evacuaees: (\d+)"
    REGEX_REROUTECOUNT = r"^# of reroute event: (\d+)"

    # data structure to contain parsed metric from file
    list_waiting_time = []
    list_trip_count = []
    list_evacuation_time = []
    list_evacuaee = []
    list_reroute_count = []
    list_filename = []

    total_parsed_file = 0
    for i, filename in enumerate(os.listdir(result_dir)):
        # file should of type text and with prefix "result"
        basename = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1]

        if extension != ".txt" or not basename.startswith("result"):
            continue

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
                result = re.search(REGEX_REROUTECOUNT, logline)
                if result is not None:
                    reroute_count = int(result.groups()[0])
                    continue
        
        if evacuee_count >= MINIMUM_EVACUEE:
            if evac_time is not None and wait_time is not None and trip_count is not None:
                list_evacuation_time.append(evac_time)
                list_waiting_time.append(wait_time)
                list_trip_count.append(trip_count)
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

    return list_evacuation_time, list_waiting_time, list_trip_count, list_evacuaee, list_filename


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("python3 solution_metric_average.py <folder path containing results file>")
        exit(0)

    # data structure to contain parsed metric from file
    list_waiting_time = []
    list_trip_count = []
    list_evacuation_time = []
    list_evacuaee = []

    dirname = sys.argv[1]
    list_evac_time, list_waiting_time, list_trip_count, list_evacuaee, list_filename = parse_data(dirname)
    
    print("average evac time {0}".format(sum(list_evac_time) / len(list_evac_time)))
    print("average wait time {0}".format(sum(list_waiting_time) / len(list_waiting_time)))
    print("average trip count {0}".format(sum(list_trip_count) / len(list_trip_count)))
    print("average evac count {0}".format(sum(list_evacuaee) / len(list_evacuaee)))
    print("average evac count {0}".format(max(list_evacuaee)))
    print("average evac time {0}".format(list_evac_time.index(min(list_evac_time))))
    print("min evac time {0}".format(min(list_evac_time)))
    print("min trip count {0}".format(min(list_trip_count)))
    print("average wait time {0}".format(max(list_waiting_time)))
    print("min evac time {0}".format(list_filename[list_evac_time.index(min(list_evac_time))]))
