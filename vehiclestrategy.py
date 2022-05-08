import simpy
import copy

from networkprimitive import Node, Edge, Route
from vehicle import Vehicle
from dispatcher import Dispatcher


class VehicleStrategy:
    def __init__(self, env: simpy.Environment, dispatcher: Dispatcher, vehicle: Vehicle):
        self.env = env
        self.dispatcher = dispatcher
        self.vehicle = vehicle
        self.forward_route_node_id_list = []
        self.backward_route_node_id_list = []

    def edge_travarse_time(self, edge: Edge) -> int:
        return int(edge.length // self.vehicle.speed)

    def plan_trip(self):
        route = self.vehicle.network.get_route(self.vehicle.route_id)
        # deep copying is needed because vehicle may travel portion of node of assigned route
        # also may update the list while running
        self.forward_route_node_id_list = copy.deepcopy(route.route_node_list)
        self.backward_route_node_id_list = list(reversed(route.route_node_list))

    def forward_pass(self):
        src = self.forward_route_node_id_list[0]
        for node_no, node_id in enumerate(self.forward_route_node_id_list[1:]):
            yield self.env.process(self.vehicle.pass_edge(self.vehicle.network.get_edge(src, node_id), pass_time=10))

            stop = self.vehicle.network.get_node(src)
            self.passenger_fill(stop)
            self.passenger_drain(stop)
            src = node_id

    def backward_pass(self):
        src = self.backward_route_node_id_list[0]
        for node_no, node_id in enumerate(self.backward_route_node_id_list[1:]):
            # reverse is done assuming that reverse edge exist even if not mentioned
            yield self.env.process(self.vehicle.pass_edge(self.vehicle.network.get_edge(node_id, src), pass_time=10))

            stop = self.vehicle.network.get_node(src)
            self.passenger_fill(stop)
            self.passenger_drain(stop)
            src = node_id

    def transfer_pass(self):
        pass

    def passenger_fill(self, stop: Node) -> int:
        demand_dict = self.vehicle.network.get_demand(stop.id)
        passenger_increase = 0
        for dest_id in demand_dict:
            if self.vehicle.passenger_count >= self.vehicle.capacity:
                break
            if dest_id not in self.forward_route_node_id_list:
                continue
            if demand_dict[dest_id] > 0:
                boarded_count = self.vehicle.passenger_in_single_dest(dest_id=dest_id, count=demand_dict[dest_id])
                stop.drain(route_id=self.vehicle.route_id, dest_id=dest_id, vehicle_id=self.vehicle.id, count=boarded_count)
                passenger_increase += boarded_count

        return passenger_increase

    def passenger_drain(self, stop: Node):
        self.vehicle.passenger_out(stop_id=stop.id)

    def signal_completion(self):
        self.dispatcher.notify(self.vehicle.id)
