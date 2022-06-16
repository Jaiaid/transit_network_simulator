import os

import simpy
import importlib.util
import sys

from network import Network
from fleet import Fleet
from strategy import VehicleStrategy, DispatchStrategy
from dispatcher import Dispatcher
from logger import Logger


class Simulator:
    def __init__(self):
        self.env: simpy.core.Environment = simpy.Environment()
        self.network: Network = Network(env=self.env)
        self.fleet: Fleet = Fleet(env=self.env)
        self.vehicle_strategy_class: VehicleStrategy = None
        self.dispatcher_strategy_class: DispatchStrategy = None
        self.stop_list = []

    def get_network(self) -> Network:
        return self.network

    '''
    will load python module on runtime
    '''
    def __load_vehicle_strategy(self, vehicle_strategy_full_import_string: str):
        import_data = vehicle_strategy_full_import_string.split(".")
        module_path = ".".join(import_data[:-1])
        # extract module name by removing .py from basepath
        module_name = ".".join(os.path.basename(module_path).split(".")[:-1])
        class_name = import_data[-1]

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        self.vehicle_strategy_class = getattr(module, class_name)

    def __load_dispatcher_strategy(self, dispatcher_strategy_full_import_string: str):
        import_data = dispatcher_strategy_full_import_string.split(".")
        module_path = ".".join(import_data[:-1])
        # extract module name by removing .py from basepath
        module_name = ".".join(os.path.basename(module_path).split(".")[:-1])
        class_name = import_data[-1]

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        self.dispatcher_strategy_class = getattr(module, class_name)

    def __load_strategy(self, strategy_script_path: str):
        self.__load_dispatcher_strategy(dispatcher_strategy_full_import_string=strategy_script_path + ".DispatchStrategy")
        self.__load_vehicle_strategy(vehicle_strategy_full_import_string=strategy_script_path + ".VehicleStrategy")

    def __load_network_data(self, networkdata_filepath: str, demanddata_filepath: str,
                            fleetdata_filepath: str, edgedata_filepath: str, stopdata_filepath: str,
                            node_class_script_path: str):
        self.network.load_network_data(network_filepath=networkdata_filepath,
                                       network_demand_filepath=demanddata_filepath,
                                       network_edgecap_filepath=edgedata_filepath,
                                       network_nodecap_filepath=stopdata_filepath,
                                       node_class_script_path=node_class_script_path)

        self.fleet.load_data(filepath=fleetdata_filepath)

    def __load_route_data(self, routedata_filepath: str, perroutestopdata_filepath: str = None):
        self.network.load_route_data(network_route_filepath=routedata_filepath)

        if perroutestopdata_filepath is not None:
            # route stop list data is given
            self.stop_list = []
            # per route stop nodes
            with open(perroutestopdata_filepath, 'r') as f:
                for line in f:
                    l = [int(_) for _ in line.split()]
                    self.stop_list.append(l)

    def get_time(self) -> int:
        return self.env.now

    def simulate(self, strategy_script_path: str, node_script_path: str,
                 networkdata_filepath: str, demanddata_filepath: str,
                 fleetdata_filepath: str, edgedata_filepath: str, stopdata_filepath: str,
                 routedata_filepath: str, perroutestopdata_filepath: str,
                 time_length: int):

        Logger.log("loading data and node class")
        self.__load_network_data(
            networkdata_filepath=networkdata_filepath,
            demanddata_filepath=demanddata_filepath,
            fleetdata_filepath=fleetdata_filepath,
            edgedata_filepath=edgedata_filepath,
            stopdata_filepath=stopdata_filepath,
            node_class_script_path=node_script_path
        )

        self.__load_route_data(routedata_filepath=routedata_filepath,
                               perroutestopdata_filepath=perroutestopdata_filepath)

        Logger.log("loading strategy classes")
        # load dispatcher and vehicle strategy
        self.__load_strategy(strategy_script_path)
        Logger.log("dispatcher strategy class : {0}".format(self.dispatcher_strategy_class))
        Logger.log("dispatcher strategy class : {0}".format(self.vehicle_strategy_class))

        dispatcher: Dispatcher = Dispatcher(fleet=self.fleet, network=self.network, env=self.env)
        # setting dispatcher strategy
        dispatcher.set_strategy(strategy_class=self.dispatcher_strategy_class)
        # start vehicle dispatch
        Logger.log("dispatching vehicle first time")
        dispatcher.start_dispatch(vehicle_strategy_class=self.vehicle_strategy_class)

        Logger.log("simulation start")
        # make dispatcher alive
        dispatcher.life_signal.succeed()
        # start whole environment
        self.env.run(until=time_length)

    def stop_simulation(self):
        pass
