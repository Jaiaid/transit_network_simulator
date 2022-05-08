import simpy

from dispatcher import Dispatcher
from network import Network
from vehicle import Vehicle

class DispatchStrategy:
    def __init__(self, dispatcher: Dispatcher, env: simpy.Environment):
        self.dispatcher: Dispatcher = dispatcher
        self.env = env

    def assign_route(self, network: Network):
        # basic round robin assignment
        route_id = 0
        for vehicle_id in self.dispatcher.fleet.vehicle_dict:
            self.dispatcher.fleet.vehicle_dict[vehicle_id].route_id = self.dispatcher.network.route_list[route_id].id
            route_id += 1
            route_id %= len(self.dispatcher.network.route_list)

    def update_route(self, network: Network, vehicle: Vehicle) -> bool:
        if any(self.dispatcher.completion_flag):
            pass
        return True
