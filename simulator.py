import simpy
import importlib

from network import Network
from fleet import Fleet
from vehiclestrategy import VehicleStrategy
from dispatchstrategy import DispatchStrategy
from dispatcher import Dispatcher
from logger import Logger

SIMTIME_MAX = 10000000


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
    def load_vehicle_strategy(self, vehicle_strategy_full_import_string: str):
        try:
            import_data = vehicle_strategy_full_import_string.split(".")
            module_path = ".".join(import_data[:-1])
            class_name = import_data[-1]
            module = importlib.import_module(module_path)
            self.vehicle_strategy_class = getattr(module, class_name)
        except ModuleNotFoundError or AttributeError as e:
            print(e)
            assert False, "exception in setting strategy, should exit"

    def load_dispatcher_strategy(self, dispatcher_strategy_full_import_string: str):
        try:
            import_data = dispatcher_strategy_full_import_string.split(".")
            module_path = ".".join(import_data[:-1])
            class_name = import_data[-1]
            module = importlib.import_module(module_path)
            self.dispatcher_strategy_class = getattr(module, class_name)
        except ModuleNotFoundError or AttributeError as e:
            print(e)
            assert False, "exception in setting strategy, should exit"

    def load_strategy(self, dispatcher_strategy_full_import_string: str, vehicle_strategy_full_import_string: str):
        self.load_dispatcher_strategy(dispatcher_strategy_full_import_string=dispatcher_strategy_full_import_string)
        self.load_vehicle_strategy(vehicle_strategy_full_import_string=vehicle_strategy_full_import_string)

    def load_data(self, networkdata_filepath: str, demanddata_filepath: str, routedata_filepath: str,
                  fleetdata_filepath: str, edgedata_filepath: str, stopdata_filepath: str,
                  perroutestopdata_filepath: str = None):
        if perroutestopdata_filepath is not None:
            # route stop list data is given
            self.stop_list = []
            # per route stop nodes
            with open(perroutestopdata_filepath, 'r') as f:
                for line in f:
                    l = [int(_) for _ in line.split()]
                    self.stop_list.append(l)

        self.network.load_network_data(network_filepath=networkdata_filepath,
                                       network_demand_filepath=demanddata_filepath,
                                       network_edgecap_filepath=edgedata_filepath,
                                       network_nodecap_filepath=stopdata_filepath)
        self.network.load_route_data(network_route_filepath=routedata_filepath)

        self.fleet.load_data(filepath=fleetdata_filepath)

    def simulate(self, dispatcher_strategy_full_import_string: str, vehicle_strategy_full_import_string: str):
        Logger.log("loading strategy classes")
        # load dispatcher and vehicle strategy
        self.load_strategy(dispatcher_strategy_full_import_string, vehicle_strategy_full_import_string)
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
        self.env.run(until=SIMTIME_MAX)
