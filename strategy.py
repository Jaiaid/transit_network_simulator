import simpy
import copy

from networkprimitive import Edge
from node import Node
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

    # return next_node_id, will_stop, passenger_pick_count, will_continue, wait time
    # default implementation here goto nowhere, just signal that forward pass is complete (will_continue==False)
    def get_next_forward_node(self) -> (int, bool, int, bool, int):
        return 0, False, 0, False, 0

    # return next_node_id, will_stop, passenger_pick_count, will_continue, wait time
    # default implementation here goto nowhere, just signal that backward pass is complete (will_continue==False)
    def get_next_backward_node(self) -> (int, bool, int, bool, int):
        return 0, False, 0, False, 0

    # return next_node_id, will_stop, passenger_pick_count, will_continue, wait time
    # default implementation here goto nowhere, just signal that transfer pass is complete (will_continue==False)
    def get_next_transfer_node(self) -> (int, bool, int, bool, int):
        return 0, False, 0, False, 0

    # return how many passengers will be picked up
    # this implementation greedily takes passenger from node and returns how much passenger can be increased
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

    # offload passenger to the input Node
    def passenger_drain(self, stop: Node):
        self.vehicle.passenger_out(stop_id=stop.id)

    # notify dispatcher about backward pass completion
    def signal_completion(self):
        self.dispatcher.notify(self.vehicle.id)


class DispatchStrategy:
    def __init__(self, dispatcher: Dispatcher, env: simpy.Environment):
        self.dispatcher: Dispatcher = dispatcher
        self.env = env

    # assign route according to given network
    # this implementation just do a round robin assignment
    def assign_route(self, network: Network):
        # basic round robin assignment
        route_id = 0
        for vehicle_id in self.dispatcher.fleet.vehicle_dict:
            self.dispatcher.fleet.vehicle_dict[vehicle_id].route_id = self.dispatcher.network.route_list[route_id].id
            route_id += 1
            route_id %= len(self.dispatcher.network.route_list)

    # return two boolean
    # will transfer?, will do roundtrip again?
    def update_route(self, network: Network, vehicle: Vehicle) -> (bool, bool):
        if any(self.dispatcher.completion_flag):
            pass
        return False, False
