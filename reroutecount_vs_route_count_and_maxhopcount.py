import numpy as np
import os
import re
import sys
import matplotlib.pyplot as plotter

def parse_data(result_dir: str):
    # file parse related regex
    REGEX_ROUTECOUNT = r"^Number of routes: (\d+)"
    REGEX_REROUTECOUNT = r"^# of reroute event: (\d+)"

    # data structure to contain parsed metric from file
    list_route_count = []
    list_reroute_count = []
    list_filename = []

    total_parsed_file = 0
    for i, filename in enumerate(os.listdir(result_dir)):
        # file should of type text and with prefix "result"
        basename = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1]

        if extension != ".txt" or not basename.startswith("result"):
            continue

        reroute_count = None
        route_count = None

        filepath = os.path.join(result_dir, filename)
        print(filepath)
        with open(filepath) as fin:
            for logline in fin.readlines():
                result = re.search(REGEX_ROUTECOUNT, logline)
                if result is not None:
                    route_count = int(result.groups()[0])
                    continue
                
                result = re.search(REGEX_REROUTECOUNT, logline)
                if result is not None:
                    reroute_count = int(result.groups()[0])
                    continue
        
            if reroute_count is not None and route_count is not None:
                list_reroute_count.append(reroute_count)
                list_route_count.append(route_count)
                
        total_parsed_file += 1

    # check sanity of data parsing
    # if parsing is correct parsed file count should be equal to data point count for each metrics
    try:
        assert len(list_reroute_count) == len(list_route_count) == total_parsed_file
    except AssertionError as e:
        print("""
            mismatch in data point count and parsed file count 
            total file : {0} 
            reroute data point count : {1} 
            route data point count : {2} 
            """.format(total_parsed_file, len(list_reroute_count), len(list_route_count)))

    return list_route_count, list_reroute_count


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("python3 reroutecount_vs_route_count.py <folder path containing results file>")
        exit(0)

    # data structure to contain parsed metric from file
    list_route_count = []
    list_reroute_count = []

    dirname = sys.argv[1]
    list_route_count, list_reroute_count = parse_data(dirname)
    
    fig, ax = plotter.subplots()
    # create the first plot
    ax.set_title("rerouting count vs route count")
    ax.set_ylabel("reroute event count")
    ax.set_xlabel("number of route")
    ax.plot(list_route_count, list_reroute_count, marker='d', mfc='red', mec='k')
    # print(list_route_count, list_reroute_count)
    # plotter.show()
    plotter.savefig("rerouting_count_vs_route_count.png", dpi=300)
    
    fig, ax = plotter.subplots()
    # create the first plot
    ax.set_title("rerouting count vs max hop count")
    ax.set_ylabel("reroute event count")
    ax.set_xlabel("max_hop_count")
    ax.plot(list(range(1, len(list_reroute_count)+1)), list_reroute_count, marker='d', mfc='red', mec='k')
    # print(list_route_count, list_reroute_count)
    # plotter.show()
    plotter.savefig("rerouting_count_vs_maxhop_count.png", dpi=300)
    
    fig, ax = plotter.subplots()
    # create the first plot
    ax.set_title("route count vs max hop count")
    ax.set_ylabel("route count")
    ax.set_xlabel("max_hop_count")
    ax.plot(list(range(1, len(list_route_count)+1)), list_route_count, marker='d', mfc='red', mec='k')
    # print(list_route_count, list_reroute_count)
    # plotter.show()
    plotter.savefig("route_count_vs_maxhop_count.png", dpi=300)

