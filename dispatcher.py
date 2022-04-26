import simpy

from fleet import Fleet
from network import Network
from logger import Logger


class Dispatcher:
    def __init__(self, fleet: Fleet, network: Network, env: simpy.Environment):
        self.fleet = fleet
        self.network = network
        self.env = env
        self.vehicle_process_list: list[simpy.Process] = []
        self.life_signal = self.env.event()
        self.global_vehicle_signal = self.env.event()
        self.dispatch_flag = [False] * len(fleet)
        self.completion_flag = [False] * len(fleet)
        self.strategy = None
        self.vehicle_strategy = None

    def set_strategy(self, strategy_class: type.__class__):
        self.strategy = strategy_class(self, self.env)

    def start_dispatch(self, vehicle_strategy_class):
        # assign route to the vehicles
        self.strategy.assign_route(self.network)

        # create the vehicle processes and set their strategy
        for vehicle_id in self.fleet.vehicle_dict:
            self.fleet.vehicle_dict[vehicle_id].assign_network(self.network)
            self.fleet.vehicle_dict[vehicle_id].set_strategy(dispatcher=self, strategy_class=vehicle_strategy_class)
            self.vehicle_process_list.append(self.env.process(
                self.fleet.vehicle_dict[vehicle_id].process()))

        # add thyself as env process
        self.env.process(self.process(env=self.env))

    def process(self, env: simpy.Environment):
        yield self.life_signal
        Logger.log("dispatcher life begins")
        # signal all vehicle to start
        self.global_vehicle_signal.succeed()
        # self.dispatcher.global_vehicle_signal = env.event()
        while True:
            self.strategy.observe()
            # WARNING: DONT REMOVE FOLLOWING LINE
            yield self.env.timeout(1)

    def notify(self, vehicle_id: int):
        self.completion_flag[vehicle_id] = True
        self.dispatch_flag[vehicle_id] = False
