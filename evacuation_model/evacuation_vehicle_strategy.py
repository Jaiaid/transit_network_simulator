import simpy
import copy

from networkprimitive import Node, Route, Edge
from vehicle import Vehicle
from dispatcher import Dispatcher
from vehiclestrategy import VehicleStrategy

RETURN_DELAY = 10
STOP_WAIT_TIME = 10


class TransitVehicleStrategy(VehicleStrategy):
    def __init__(self, env: simpy.Environment, dispatcher: Dispatcher, vehicle: Vehicle):
        self.env = env
        self.dispatcher = dispatcher
        self.vehicle = vehicle
        self.forward_route_node_id_list = []
        self.backward_route_node_id_list = []
        self.node_id_demand_dict = {}

    def edge_travarse_time(self, edge: Edge) -> int:
        return int(edge.length / self.vehicle.speed)

    def plan_trip(self):
        route = self.vehicle.network.get_route(self.vehicle.route_id)
        # deep copying is needed because vehicle may travel portion of node of assigned route
        # also may update the list while running
        self.forward_route_node_id_list = copy.deepcopy(route.route_node_list)
        self.backward_route_node_id_list = list(reversed(route.route_node_list))
        self.node_id_demand_dict = {}

        for node_id in self.forward_route_node_id_list:
            demand = self.vehicle.network.get_demand(node_id=node_id)[self.forward_route_node_id_list[-1]]
            if demand > 0:
                self.node_id_demand_dict[node_id] = demand

    def forward_pass(self):
        src = self.forward_route_node_id_list[0]
        for node_no, node_id in enumerate(self.forward_route_node_id_list[1:]):
            edge = self.vehicle.network.get_edge(src, node_id)
            yield self.env.process(self.vehicle.enter(edge=edge, pass_time=self.edge_travarse_time(edge=edge)))

            if node_id in self.node_id_demand_dict:
                stop = self.vehicle.network.get_node(src)
                self.passenger_fill(stop)
                self.passenger_drain(stop)
                yield self.env.process(self.vehicle.wait(time=STOP_WAIT_TIME))
            src = node_id

        src = self.backward_route_node_id_list[0]
        for node_no, node_id in enumerate(self.backward_route_node_id_list[1:]):
            # reverse is done assuming that reverse edge exist even if not mentioned
            edge = self.vehicle.network.get_edge(node_id, src)
            yield self.env.process(self.vehicle.enter(edge=edge, pass_time=self.edge_travarse_time(edge=edge)))

            if node_id in self.node_id_demand_dict and self.node_id_demand_dict[node_id] == 0:
                break

    def backward_pass(self):
        yield self.env.process(self.vehicle.wait(time=RETURN_DELAY))

    def passenger_fill(self, stop: Node):
        demand_dict = self.vehicle.network.get_demand(stop.id)
        for dest_id in demand_dict:
            if demand_dict[dest_id] > 0:
                boarded_count = self.vehicle.passenger_in_single_dest(dest_id=dest_id, count=demand_dict[dest_id])
                stop.drain(route_id=self.vehicle.route_id, dest_id=dest_id, vehicle_id=self.vehicle.id, count=boarded_count)
                self.node_id_demand_dict[dest_id] -= boarded_count
                if self.vehicle.passenger_count >= self.vehicle.capacity:
                    break

    def passenger_drain(self, stop: Node):
        self.vehicle.passenger_out(stop_id=stop.id)

    def signal_completion(self):
        self.dispatcher.notify(self.vehicle.id)
