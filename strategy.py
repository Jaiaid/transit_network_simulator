import simpy
import copy

from networkprimitive import Node, Edge, Route
from network import Network
from vehicle import Vehicle
from dispatcher import Dispatcher


class VehicleStrategy:
    def __init__(self, env: simpy.Environment, dispatcher: Dispatcher, vehicle: Vehicle):
        self.env = env
        self.dispatcher = dispatcher
        self.vehicle = vehicle
        self.forward_route_node_id_list = []
        self.backward_route_node_id_list = []

    def edge_travarse_time(self, edge: Edge) -> float:
        return edge.length / self.vehicle.speed

    def plan_trip(self):
        route = self.vehicle.network.get_route(self.vehicle.route_id)
        # deep copying is needed because vehicle may travel portion of node of assigned route
        # also may update the list while running
        self.forward_route_node_id_list = copy.deepcopy(route.route_node_list)
        self.backward_route_node_id_list = list(reversed(route.route_node_list))

    def forward_pass(self):
        src = self.forward_route_node_id_list[0]
        for node_no, node_id in enumerate(self.forward_route_node_id_list[1:]):
            edge = self.vehicle.network.get_edge(src, node_id)
            yield self.env.process(self.vehicle.pass_edge(edge=edge, pass_time=self.edge_travarse_time(edge=edge)))

            stop = self.vehicle.network.get_node(src)
            self.passenger_fill(stop)
            self.passenger_drain(stop)
            src = node_id

    def backward_pass(self):
        src = self.backward_route_node_id_list[0]
        for node_no, node_id in enumerate(self.backward_route_node_id_list[1:]):
            # reverse is done assuming that reverse edge exist even if not mentioned
            edge = self.vehicle.network.get_edge(node_id, src)
            yield self.env.process(self.vehicle.pass_edge(edge=edge, pass_time=self.edge_travarse_time(edge=edge)))

            stop = self.vehicle.network.get_node(src)
            self.passenger_fill(stop)
            self.passenger_drain(stop)
            src = node_id

    def transfer_pass(self):
        yield self.env.timeout(2)

    def get_next_forward_node(self) -> (int, bool, int, bool):
        return 0, False, 0, False

    def get_next_backward_node(self) -> (int, bool, int, bool):
        return 0, False, 0, False

    def get_next_transfer_node(self) -> (int, bool, int, bool):
        return 0, False, 0, False

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
