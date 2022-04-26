import argparse
import os

from simulator import Simulator
from graph_generator import GraphGenerator
from logger import Logger

if __name__ == "__main__":
    # edit file path here to change data source
    parser = argparse.ArgumentParser()
    parser.add_argument("-input", "--input_dir", help="folder path containing the input files", required=True)
    parser.add_argument("-ds", "--dispatch_strategy", help="which strategy will be followed by vehicle dispatcher",
                        required=True)
    parser.add_argument("-vs", "--vehicle_strategy", help="which strategy will be followed by vehicle in transporting",
                        required=True)
    parser.add_argument("-eplot", "--evactime_plot", help="", default="false", required=False)
    parser.add_argument("-tplot", "--tripcomplete_plot", help="", default="false", required=False)
    args = parser.parse_args()

    nodecap_filepath = "{0}/stopcap.txt".format(args.input_dir)
    edgecap_filepath = "{0}/edgecap.txt".format(args.input_dir)
    network_filepath = "{0}/network.txt".format(args.input_dir)
    demand_filepath = "{0}/demand.txt".format(args.input_dir)
    fleet_filepath = "{0}/fleet.txt".format(args.input_dir)
    route_filepath = "{0}/route.txt".format(args.input_dir)
    routestop_filepath = None

    if os.path.exists("{0}/route_stops.txt".format(args.input_dir)):
        routestop_filepath = "{0}/route_stops.txt".format(args.input_dir)

    # init necessary class and modules
    simulator: Simulator = Simulator()
    graph_generator: GraphGenerator = GraphGenerator()
    Logger.init()

    # provide datafile and prepare internal datastructure and environment
    simulator.load_data(
        networkdata_filepath=network_filepath,
        demanddata_filepath=demand_filepath,
        routedata_filepath=route_filepath,
        fleetdata_filepath=fleet_filepath,
        edgedata_filepath=edgecap_filepath,
        stopdata_filepath=nodecap_filepath,
        perroutestopdata_filepath=routestop_filepath
    )

    # simulate
    simulator.simulate(dispatcher_strategy_full_import_string=args.dispatch_strategy,
                       vehicle_strategy_full_import_string=args.vehicle_strategy)

    # close the logger as graph_generator will need the file
    Logger.close()
    # generate graph
    graph_generator.generate()
