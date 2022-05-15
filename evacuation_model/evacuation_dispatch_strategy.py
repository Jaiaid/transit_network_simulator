import simpy
import random

from dispatcher import Dispatcher
from network import Network
from vehicle import Vehicle

# 2 minute gap between each fleet
FLEET_DEPARTURE_TIME_GAP_SEC = 120


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

    def update_route(self, network: Network, vehicle: Vehicle) -> bool:
        # calculate remaining demand
        self.route_demand_dict[vehicle.route_id] = self.__calculate_demand(network, vehicle.route_id)
        if self.route_demand_dict[vehicle.route_id] > 0:
            return True
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
                return True
            attempt_count += 1

        return False
