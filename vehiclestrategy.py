import simpy

from networkprimitive import Node, Route
from vehicle import Vehicle
from dispatcher import Dispatcher


class VehicleStrategy:
    def __init__(self, env: simpy.Environment, dispatcher: Dispatcher, vehicle: Vehicle):
        self.env = env
        self.dispatcher = dispatcher
        self.vehicle = vehicle

    def forward_pass(self):
        route = self.vehicle.network.get_route(self.vehicle.route_id)
        src = route.route_node_list[0]
        for node_no, node_id in enumerate(route.route_node_list[1:]):
            yield self.env.process(self.vehicle.enter(self.vehicle.network.get_edge(src, node_id), pass_time=10))
            src = node_id

    def backward_pass(self):
        route = self.vehicle.network.get_route(self.vehicle.route_id)
        src = route.route_node_list[-1]
        for node_no, node_id in enumerate(list(reversed(route.route_node_list))[1:]):
            yield self.env.process(self.vehicle.enter(self.vehicle.network.get_edge(src, node_id), pass_time=10))
            src = node_id

    def passenger_fill(self, vehicle: Vehicle, stop: Node):
        pass

    def passenger_drain(self, vehicle: Vehicle, stop: Node):
        pass

    def signal_completion(self):
        self.dispatcher.notify(self.vehicle.id)


class SimpleVehicleStrategy(VehicleStrategy):
    pass


# class SimilarReturnVehicleStrategy(VehicleStrategy):
#     # def route_process(self, simulator: Simulator, fleet_number: str, capacity: int, route: list, interval: float,
#     #                   trip: int, route_stop_list: list, return_route_stop_list: list = None):
