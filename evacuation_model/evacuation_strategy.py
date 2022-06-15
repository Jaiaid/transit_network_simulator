import simpy
import copy
import random

from networkprimitive import Edge
from dispatcher import Dispatcher
from network import Network
from vehicle import Vehicle
from evacuation_node import Node

# 2 minute gap between each fleet
FLEET_DEPARTURE_TIME_GAP_SEC = 120
# vehicle waiting times
STOP_STANDING_TIME = 0.5
SHELTER_EVACUATION_TIME = 1


class DispatchStrategy:
    def __init__(self, dispatcher: Dispatcher, env: simpy.Environment):
        self.dispatcher: Dispatcher = dispatcher
        self.env = env
        self.route_demand_dict = {}

    def __calculate_demand(self, network: Network, route_id: int) -> int:
        route = network.get_route(route_id)
        # TODO
        # a node may be part of multiple route
        # current demand calculation consider full demand while adding,
        # this creates overestimation when we try to use it for all route to calculate total demand
        demand = 0
        for node_id in route.route_node_list:
            demand_dict = network.get_demand(node_id=node_id)
            for dest_id in demand_dict:
                if dest_id in route.route_node_list:
                    demand += demand_dict[dest_id]

        return demand

    def assign_route(self, network: Network):
        # to control departure time of fleet assigned in a route
        route_id_to_latest_departure_time_dict = {}
        # assigning fleet proportionate to demand
        self.route_demand_dict = {}
        total_demand = 0
        for route_id, route in enumerate(network.route_list):
            self.route_demand_dict[route_id] = self.__calculate_demand(network, route_id)
            total_demand += self.route_demand_dict[route_id]

        # assign route to the vehicle
        start_vehicle_id = 0
        total_assigned = 0
        for route_id in self.route_demand_dict:
            assigned_vehicle_count = int(self.route_demand_dict[route_id] * len(self.dispatcher.fleet.vehicle_dict)
                                         // total_demand)
            end_vehicle_id = start_vehicle_id + assigned_vehicle_count

            if route_id not in route_id_to_latest_departure_time_dict:
                route_id_to_latest_departure_time_dict[route_id] = 0

            for vehicle_id in range(start_vehicle_id, end_vehicle_id):
                # set route id
                self.dispatcher.fleet.vehicle_dict[vehicle_id].route_id =\
                    self.dispatcher.network.route_list[route_id].id
                # set current position
                self.dispatcher.fleet.vehicle_dict[vehicle_id].current_node_id =\
                    self.dispatcher.network.get_route(route_id=route_id).route_node_list[0]
                # set departure time
                self.dispatcher.fleet.vehicle_dict[vehicle_id].set_departure_time(
                    departure_time=route_id_to_latest_departure_time_dict[route_id]
                )

                # increase the latest departure time for next vehicle
                route_id_to_latest_departure_time_dict[route_id] += FLEET_DEPARTURE_TIME_GAP_SEC
            start_vehicle_id = end_vehicle_id
            total_assigned += assigned_vehicle_count

        if total_assigned < self.dispatcher.fleet.size():
            # assign remaining vehicles in roundrobin fashion
            route_id = 0
            for vehicle_id in range(total_assigned, self.dispatcher.fleet.size()):
                # set route id
                self.dispatcher.fleet.vehicle_dict[vehicle_id].route_id = route_id
                # set current position
                self.dispatcher.fleet.vehicle_dict[vehicle_id].current_node_id = \
                    self.dispatcher.network.get_route(route_id=route_id).route_node_list[0]
                # set departure time
                self.dispatcher.fleet.vehicle_dict[vehicle_id].set_departure_time(
                    departure_time=route_id_to_latest_departure_time_dict[route_id]
                )
                # increase the latest departure time for next vehicle
                route_id_to_latest_departure_time_dict[route_id] += FLEET_DEPARTURE_TIME_GAP_SEC

                route_id += 1
                route_id %= len(self.dispatcher.network.route_list)

    def update_route(self, network: Network, vehicle: Vehicle) -> (bool, bool):
        # calculate remaining demand
        self.route_demand_dict[vehicle.route_id] = self.__calculate_demand(network, vehicle.route_id)
        if self.route_demand_dict[vehicle.route_id] > 0:
            # route not updated but do roundtrip again
            return False, True
        # TODO:
        # implement a proper mechanism to detect all route demand is staisfied
        attempt_count = 0
        while attempt_count < len(network.route_list):
            random_route = random.choice(network.route_list)
            # assign the new route if it has some passengers to serve and
            # currently vehicle is at the last node of this route
            if self.route_demand_dict[random_route.id] > 0 and \
                    random_route.route_node_list[-1] == vehicle.current_node_id:
                vehicle.route_id = random_route.id
                # route updated and do roundtrip again
                return True, True
            attempt_count += 1

        # route not updated and don't do roundtrip again
        return False, False


class VehicleStrategy:
    def __init__(self, env: simpy.Environment, dispatcher: Dispatcher, vehicle: Vehicle):
        self.env = env
        self.dispatcher = dispatcher
        self.vehicle = vehicle
        self.forward_route_node_id_list = []
        self.backward_route_node_id_list = []
        self.node_id_demand_dict = {}
        # keeps counter of current position in node list
        # used in forward pass, backward pass, transfer pass
        # should be reset to zero after completion of each pass
        self.route_list_current_idx = 0
        # needed in evacuation model to evacuate do roundtrip greedily
        self.refined_backward_route_node_id_list = []

    @staticmethod
    def __id_first_occurance_idx(id_list: list[int], element: int) -> int:
        return id_list.index(element)

    def __calculated_backward_route(self):
        # first evaluate if backward pass needs refining
        # as passengers are picked up greedily from earlier stop,
        # it maybe the case that vehicle don't need to return at the beginning to continue the loop
        # think like bubble sort
        self.refined_backward_route_node_id_list = [self.backward_route_node_id_list[0]]
        node_id_list_inbetween_stops = []

        for node_no, node_id in enumerate(self.backward_route_node_id_list[1:]):
            if node_id in self.node_id_demand_dict and self.node_id_demand_dict[node_id] == 0:
                break
            elif node_id in self.node_id_demand_dict and self.node_id_demand_dict[node_id] > 0:
                self.refined_backward_route_node_id_list += node_id_list_inbetween_stops
                self.refined_backward_route_node_id_list.append(node_id)
                node_id_list_inbetween_stops = []
            else:
                node_id_list_inbetween_stops.append(node_id)

    def edge_travarse_time(self, edge: Edge) -> float:
        return edge.length / self.vehicle.speed

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

    # return next_node_id, will_stop, passenger_pick_count, will_continue, wait time
    def get_next_forward_node(self) -> (int, bool, int, bool, int):
        # TODO
        # as a node may be repeated start_node_idx may not be the index of first appearance
        # start_node_idx = self.forward_route_node_id_list.index(self.vehicle.current_node_id)
        src = self.vehicle.current_node_id
        next_node_id = -1
        wait_time = 0
        passenger_pick_count = 0
        will_stop = False
        will_continue = False

        # as it is evacuation scenario last node will not have any demand but it will drain passenger
        if src in self.node_id_demand_dict or self.route_list_current_idx + 1 == len(self.forward_route_node_id_list):
            stop = self.vehicle.network.get_node(src)
            self.passenger_fill(stop)
            self.passenger_drain(stop)
            will_stop = True
            wait_time = STOP_STANDING_TIME + SHELTER_EVACUATION_TIME

        if self.route_list_current_idx + 1 < len(self.forward_route_node_id_list):
            next_node_id = self.forward_route_node_id_list[self.route_list_current_idx + 1]
            will_continue = True
            # update at which position of current node list we will be in
            self.route_list_current_idx += 1
        else:
            wait_time = STOP_STANDING_TIME + SHELTER_EVACUATION_TIME
            # resetting the index as no next node in forward pass
            self.route_list_current_idx = 0

        return next_node_id, will_stop, passenger_pick_count, will_continue, wait_time

    def get_next_backward_node(self) -> (int, bool, int, bool, int):
        # if vehicle is at first node of backward pass let's calculated the backward pass node list
        if self.route_list_current_idx == 0:
            self.__calculated_backward_route()

        next_node_id = -1
        wait_time = 0
        passenger_pick_count = 0
        will_stop = False
        will_continue = False

        if len(self.refined_backward_route_node_id_list) > 1 and \
                self.route_list_current_idx + 1 < len(self.refined_backward_route_node_id_list):
            next_node_id = self.refined_backward_route_node_id_list[self.route_list_current_idx + 1]
            will_continue = True
            # update at which position of current node list we will be in
            self.route_list_current_idx += 1
        else:
            # resetting the index as no next node in backward pass
            self.route_list_current_idx = \
                len(self.forward_route_node_id_list) - len(self.refined_backward_route_node_id_list)
            self.signal_completion()

        return next_node_id, will_stop, passenger_pick_count, will_continue, wait_time

    def get_next_transfer_node(self) -> (int, bool, int, bool, int):
        # if vehicle is will start at node of backward pass let's calculated the backward pass node list
        if self.route_list_current_idx == 0:
            self.backward_route_node_id_list =\
                list(reversed(self.vehicle.network.get_route(self.vehicle.route_id).route_node_list))

        next_node_id = -1
        wait_time = 0
        passenger_pick_count = 0
        will_stop = False
        will_continue = False

        if self.route_list_current_idx + 1 < len(self.backward_route_node_id_list):
            next_node_id = self.backward_route_node_id_list[self.route_list_current_idx + 1]
            will_continue = True
            # update at which position of current node list we will be in
            self.route_list_current_idx += 1
        else:
            # resetting the index as no next node in backward pass
            self.route_list_current_idx = 0

        return next_node_id, will_stop, passenger_pick_count, will_continue, wait_time

    def forward_pass(self):
        # TODO
        # as a node may be repeated start_node_idx may not be the index of first appearance
        start_node_idx = self.forward_route_node_id_list.index(self.vehicle.current_node_id)
        src = self.vehicle.current_node_id

        for i in range(start_node_idx+1, len(self.forward_route_node_id_list)):
            # to board passenger from node
            yield self.env.process(self.vehicle.wait(time=STOP_STANDING_TIME))
            if src in self.node_id_demand_dict:
                stop = self.vehicle.network.get_node(src)
                self.passenger_fill(stop)
                self.passenger_drain(stop)
                yield self.env.process(self.vehicle.wait(time=SHELTER_EVACUATION_TIME))

            node_id = self.forward_route_node_id_list[i]
            edge = self.vehicle.network.get_edge(src, node_id)
            yield self.env.process(self.vehicle.pass_edge(edge=edge, pass_time=self.edge_travarse_time(edge=edge)))
            src = node_id
            # vehicle now in different node
            self.vehicle.current_node_id = src

        # to drain the passengers at the last node
        yield self.env.process(self.vehicle.wait(time=STOP_STANDING_TIME))
        stop = self.vehicle.network.get_node(src)
        self.passenger_fill(stop)
        self.passenger_drain(stop)
        yield self.env.process(self.vehicle.wait(time=SHELTER_EVACUATION_TIME))

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
            elif node_id in self.node_id_demand_dict and self.node_id_demand_dict[node_id] > 0:
                refined_backward_route_node_id_list += node_id_list_inbetween_stops
                refined_backward_route_node_id_list.append(node_id)
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
            # vehicle now in different node
            self.vehicle.current_node_id = src
        else:
            self.signal_completion()
            self.vehicle.current_node_id = refined_backward_route_node_id_list[0]

    def transfer_pass(self):
        newly_assigned_backward_route_node_id_list = \
            list(reversed(self.vehicle.network.get_route(self.vehicle.route_id).route_node_list))

        src = newly_assigned_backward_route_node_id_list[0]
        for node_no, node_id in enumerate(newly_assigned_backward_route_node_id_list[1:]):
            # reverse is done assuming that reverse edge exist even if not mentioned
            edge = self.vehicle.network.get_edge(node_id, src)
            yield self.env.process(self.vehicle.pass_edge(edge=edge, pass_time=self.edge_travarse_time(edge=edge)))

            src = node_id
        self.vehicle.current_node_id = src

    def passenger_fill(self, stop: Node) -> int:
        demand_dict = self.vehicle.network.get_demand(stop.id)
        passenger_increase = 0

        for dest_id in demand_dict:
            # in evacuation model we are only serving demand to shelter which is at the end of the route
            if dest_id != self.forward_route_node_id_list[-1]:
                continue
            if self.vehicle.passenger_count >= self.vehicle.capacity:
                break
            if demand_dict[dest_id] > 0:
                boarded_count = self.vehicle.passenger_in_single_dest(dest_id=dest_id, count=demand_dict[dest_id])
                stop.drain(route_id=self.vehicle.route_id, dest_id=dest_id, vehicle_id=self.vehicle.id,
                           count=boarded_count)
                passenger_increase += boarded_count
                self.node_id_demand_dict[stop.id] -= boarded_count

        return passenger_increase

    def passenger_drain(self, stop: Node):
        self.vehicle.passenger_out(stop_id=stop.id)

    def signal_completion(self):
        self.dispatcher.notify(self.vehicle.id)
