import argparse
import os

from simulator import Simulator
from graph_generator import GraphGenerator
from logger import Logger

if __name__ == "__main__":
    # edit file path here to change data source
    parser = argparse.ArgumentParser()
    parser.add_argument("-input", "--input_dir", help="folder path containing the input files", required=True)
    parser.add_argument("-sim", "--simulate", help="if will simulate from input data", action='store_true',
                        default=False, required=False)
    parser.add_argument("-simtime", "--simulate_time_length", help="how many unit time to simulate", type=int,
                        default=3600, required=False)
    parser.add_argument("-al", "--analyze", help="if will analyze even-log.txt and generate graphs", action='store_true',
                        default=False, required=False)
    parser.add_argument("-ts", "--time_step", help="time step used in generate data point for graphs", type=int,
                        default=600, required=False)
    parser.add_argument("-st", "--strategy_class_script_path",
                        help="script path containing VehicleStrategy and DispatchStrategy class",
                        required=True)
    parser.add_argument("-nc", "--node_class_script_path", help="script path containing Node class",
                        required=True)
    parser.add_argument("-velplot", "--avgvelocity_plot", help="if will generate avg velocity plot at given time step",
                        default=False, required=False)
    parser.add_argument("-eplot", "--evactime_plot", help="if will generate evacuation time plot", default=False,
                        required=False)
    parser.add_argument("-tplot", "--tripcomplete_plot", help="if will generate hourly trip completion count plot",
                        default=False, required=False)

    args = parser.parse_args()

    # simulate
    if args.simulate:
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

        # provide datafile and prepare internal datastructure and environment

        Logger.init()

        # they maybe provided in steps but maybe it will be easier to give one public method
        simulator.simulate(strategy_script_path=args.strategy_class_script_path,
                           node_script_path=args.node_class_script_path,
                           time_length=args.simulate_time_length)
        # close the logger as graph_generator will need the file
        Logger.close()

    # generate graph
    if args.analyze:
        graph_generator: GraphGenerator = GraphGenerator()
        graph_generator.generate(avg_velocity_time_step_sec=args.time_step)
