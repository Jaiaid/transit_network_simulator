import simpy
import copy

from networkprimitive import Node, Route, Edge
from vehicle import Vehicle
from dispatcher import Dispatcher
from vehiclestrategy import VehicleStrategy

STOP_STANDING_TIME = 0.5
SHELTER_EVACUATION_TIME = 1


class TransitVehicleStrategy(VehicleStrategy):
    def __init__(self, env: simpy.Environment, dispatcher: Dispatcher, vehicle: Vehicle):
        self.env = env
        self.dispatcher = dispatcher
        self.vehicle = vehicle
        self.forward_route_node_id_list = []
        self.backward_route_node_id_list = []
        self.node_id_demand_dict = {}

    @staticmethod
    def __id_first_occurance_idx(id_list: list[int], element: int) -> int:
        return id_list.index(element)

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
        start_node_idx = self.forward_route_node_id_list.index(self.vehicle.current_node_id)
        src = self.vehicle.current_node_id

        for i in range(start_node_idx+1, len(self.forward_route_node_id_list)):
            node_id = self.forward_route_node_id_list[i]
            edge = self.vehicle.network.get_edge(src, node_id)
            yield self.env.process(self.vehicle.pass_edge(edge=edge, pass_time=self.edge_travarse_time(edge=edge)))

            yield self.env.process(self.vehicle.wait(time=STOP_STANDING_TIME))
            if node_id in self.node_id_demand_dict:
                stop = self.vehicle.network.get_node(src)
                self.passenger_fill(stop)
                self.passenger_drain(stop)
                yield self.env.process(self.vehicle.wait(time=SHELTER_EVACUATION_TIME))
            src = node_id

    def backward_pass(self):
        # first evaluate if backward pass needs refining
        # as passengers are picked up greedily from earlier stop,
        # it maybe the case that vehicle don't need to return at the beginning to continue the loop
        # think like bubble sort
        refined_backward_route_node_id_list = [self.backward_route_node_id_list[0]]
        node_id_list_inbetween_stops = []
        for node_no, node_id in enumerate(self.backward_route_node_id_list[1:]):
            if node_id in self.node_id_demand_dict and self.node_id_demand_dict[node_id] == 0:
                break
            elif node_id in self.node_id_demand_dict and self.node_id_demand_dict[node_id] == 0:
                refined_backward_route_node_id_list += node_id_list_inbetween_stops
                node_id_list_inbetween_stops = []
            else:
                node_id_list_inbetween_stops.append(node_id)

        if len(refined_backward_route_node_id_list) > 1:
            src = refined_backward_route_node_id_list[0]
            for node_no, node_id in enumerate(refined_backward_route_node_id_list[1:]):
                # reverse is done assuming that reverse edge exist even if not mentioned
                edge = self.vehicle.network.get_edge(node_id, src)
                yield self.env.process(self.vehicle.pass_edge(edge=edge, pass_time=self.edge_travarse_time(edge=edge)))

                src = node_id
                if node_id in self.node_id_demand_dict and self.node_id_demand_dict[node_id] == 0:
                    break
            self.vehicle.current_node_id = src
        else:
            self.signal_completion()
            self.vehicle.current_node_id = refined_backward_route_node_id_list[0]
        # route = self.vehicle.network.get_route(self.vehicle.route_id)
        # self.backward_route_node_id_list = list(reversed(route.route_node_list))
        #
        # src = self.backward_route_node_id_list[0]
        # start_node_idx = len(self.forward_route_node_id_list) - 1
        # for node_no, node_id in enumerate(self.backward_route_node_id_list[1:]):
        #     # reverse is done assuming that reverse edge exist even if not mentioned
        #     edge = self.vehicle.network.get_edge(node_id, src)
        #     yield self.env.process(self.vehicle.enter(edge=edge, pass_time=self.edge_travarse_time(edge=edge)))
        #
        #     src = node_id
        #     start_node_idx -= 1

    # TODO
    # transfer pass implementation
    def transfer_pass(self):
        pass

    def passenger_fill(self, stop: Node) -> int:
        demand_dict = self.vehicle.network.get_demand(stop.id)
        passenger_increase = 0
        for dest_id in demand_dict:
            if demand_dict[dest_id] > 0:
                boarded_count = self.vehicle.passenger_in_single_dest(dest_id=dest_id, count=demand_dict[dest_id])
                stop.drain(route_id=self.vehicle.route_id, dest_id=dest_id, vehicle_id=self.vehicle.id,
                           count=boarded_count)
                self.node_id_demand_dict[dest_id] -= boarded_count
                passenger_increase += boarded_count
                if self.vehicle.passenger_count >= self.vehicle.capacity:
                    break
        return passenger_increase

    def passenger_drain(self, stop: Node):
        self.vehicle.passenger_out(stop_id=stop.id)

    def signal_completion(self):
        self.dispatcher.notify(self.vehicle.id)
