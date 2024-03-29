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
        network_filepath = "{0}/network.txt".format(args.input_dir)
        demand_filepath = "{0}/demand.txt".format(args.input_dir)
        fleet_filepath = "{0}/fleet.txt".format(args.input_dir)
        route_filepath = "{0}/route.txt".format(args.input_dir)
        # edgecap file is same as network file if not provided
        # later condition will check for existance and update the path if found
        edgecap_filepath = "{0}/network.txt".format(args.input_dir)
        routestop_filepath = None
        nodecap_filepath = None

        # check if edgecap file exists, if not inform user in console that it does not exist
        if os.path.exists("{0}/edgecap.txt".format(args.input_dir)):
            edgecap_filepath = "{0}/edgecap.txt".format(args.input_dir)
        else:
            print(
                "edgecap.txt not found in input directory, network.txt will be used as edge capacity data"
            )
        if os.path.exists("{0}/route_stops.txt".format(args.input_dir)):
            routestop_filepath = "{0}/route_stops.txt".format(args.input_dir)
        if os.path.exists("{0}/stopcap.txt".format(args.input_dir)):
            nodecap_filepath = "{0}/stopcap.txt".format(args.input_dir)

        # init necessary class and modules
        simulator: Simulator = Simulator()

        # provide datafile and prepare internal datastructure and environment

        Logger.init()

        # they maybe provided in steps but maybe it will be easier to give one public method
        simulator.simulate(strategy_script_path=args.strategy_class_script_path,
                           node_script_path=args.node_class_script_path, networkdata_filepath=network_filepath,
                           demanddata_filepath=demand_filepath, fleetdata_filepath=fleet_filepath,
                           edgedata_filepath=edgecap_filepath, stopdata_filepath=nodecap_filepath,
                           routedata_filepath=route_filepath, perroutestopdata_filepath=routestop_filepath,
                           time_length=args.simulate_time_length)
        # close the logger as graph_generator will need the file
        Logger.close()

    # generate graph
    if args.analyze:
        graph_generator: GraphGenerator = GraphGenerator()
        graph_generator.generate(avg_velocity_time_step_sec=args.time_step)

        total_served_passenger = graph_generator.get_total_served_passenger()
        last_passenger_serve_data = graph_generator.get_last_passenger_served_data()
        last_trip_completion_data = graph_generator.get_last_trip_completion_data()

        print("total served passenger : {0}".format(total_served_passenger))
        print("Last passenger is offloaded by vehicle {0} at time {1} in stop {2} and route {3}".format(
                last_passenger_serve_data[1], last_passenger_serve_data[0], last_passenger_serve_data[2],
                last_passenger_serve_data[3]
            )
        )
        print("Last trip is complete by vehicle {0} at time {1} in route {2}".format(
            last_trip_completion_data[1], last_trip_completion_data[0], last_trip_completion_data[2]
        ))
        print("graphs are saved in {0}".format(os.path.abspath(os.path.curdir)))
