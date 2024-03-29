import simpy

from network import Network
from logger import Logger


class Vehicle:
    def __init__(self, vehicle_id: int, capacity: int, length: float, speed: float, env: simpy.Environment):
        self.id = vehicle_id
        self.dest_id_passenger_dict = {}
        self.capacity = capacity
        self.passenger_count = 0
        self.length = length
        self.speed = speed
        self.trip_count = 0
        self.departure_time = 0
        self.current_node_id = -1
        self.env = env
        self.dispatcher_signal = self.env.event()
        self.network: Network = None
        self.route_id: int = None
        self.dispatcher = None
        self.strategy = None
        self.repeat = True
        self.current_pass_type = None

    def switch_to_forward_pass(self):
        self.current_pass_type = 'f'

    def switch_to_backward_pass(self):
        self.current_pass_type = 'b'

    def switch_to_transfer_pass(self):
        self.current_pass_type = 't'

    def set_departure_time(self, departure_time: int):
        self.departure_time = departure_time

    def set_strategy(self, dispatcher, strategy_class: type.__class__):
        self.dispatcher = dispatcher
        self.strategy = strategy_class(self.env, self.dispatcher, self)

    def pass_edge(self, edge, pass_time: float):
        # for container resource put and get needs to be done explicitly
        # putting length amount in the container
        with edge.put(self.length) as req:
            yield req
            Logger.log(
                "route {0} vehicle {1} entering edge {2},{3} of length {4} at {5:.0f}".format(
                    self.route_id, self.id, edge.src_id, edge.dst_id, edge.length, self.env.now)
            )
            yield self.env.timeout(pass_time)
        # get amount out before leaving
        with edge.get(self.length) as req:
            yield req
            Logger.log(
                "route {0} vehicle {1} leaving edge {2},{3} of length {4} at {5:.0f}".format(
                    self.route_id, self.id, edge.src_id, edge.dst_id, edge.length, self.env.now)
            )

    def leave(self):
        pass

    def wait(self, time: float):
        Logger.log("route {0} vehicle {1} waiting start at {2:.0f}".format(self.route_id, self.id, self.env.now))
        yield self.env.timeout(time)
        Logger.log("route {0} vehicle {1} waiting finish at {2:.0f}".format(self.route_id, self.id, self.env.now))

    def assign_network(self, network: Network):
        self.network = network

    def passenger_in(self, dest_id_passenger_dict: dict[int, int]):
        for stop_id in dest_id_passenger_dict:
            self.passenger_count += dest_id_passenger_dict[stop_id]
            if stop_id in self.dest_id_passenger_dict:
                self.passenger_in_single_dest(dest_id=stop_id, count=dest_id_passenger_dict[stop_id])

    def passenger_in_single_dest(self, dest_id: int, count: int) -> int:
        if dest_id not in self.dest_id_passenger_dict:
            self.dest_id_passenger_dict[dest_id] = 0
        if self.passenger_count + count > self.capacity:
            remaining = count - (self.capacity - self.passenger_count)
        else:
            remaining = 0
        self.dest_id_passenger_dict[dest_id] += count - remaining
        self.passenger_count += count - remaining
        return count - remaining

    def passenger_out(self, stop_id: int):
        if stop_id in self.dest_id_passenger_dict:
            self.passenger_count -= self.dest_id_passenger_dict[stop_id]
            Logger.log(
                "route {0} vehicle {1} offloading {2} passenger for {3} at {4:.0f}".format(
                    self.route_id, self.id, self.dest_id_passenger_dict[stop_id], stop_id, self.env.now)
            )
            self.dest_id_passenger_dict[stop_id] = 0

    def __forward_pass(self):
        will_continue = True
        src = self.current_node_id
        while will_continue:
            next_node_id, will_stop, passenger_pick_count, will_continue, wait_time =\
                self.strategy.get_next_forward_node()

            # stop = self.network.get_node(self.current_node_id)
            # if will_stop:
            #     if passenger_pick_count > 0:
            #         self.strategy.passenger_fill(stop)
            #     self.strategy.passenger_drain(stop)

            if will_continue:
                edge = self.network.get_edge(src, next_node_id)
                yield self.env.process(self.pass_edge(edge=edge,
                                                      pass_time=self.strategy.edge_travarse_time(edge=edge)))
                src = next_node_id
                self.current_node_id = src

            # wait according to the wait time
            yield self.env.process(self.wait(time=wait_time))

    def __backward_pass(self):
        will_continue = True
        src = self.current_node_id
        while will_continue:
            next_node_id, will_stop, passenger_pick_count, will_continue, wait_time =\
                self.strategy.get_next_backward_node()

            # stop = self.network.get_node(self.current_node_id)
            # if will_stop:
            #     if passenger_pick_count > 0:
            #         self.strategy.passenger_fill(stop)
            #     self.strategy.passenger_drain(stop)

            if will_continue:
                edge = self.network.get_edge(src, next_node_id)
                yield self.env.process(self.pass_edge(edge=edge,
                                                      pass_time=self.strategy.edge_travarse_time(edge=edge)))
                src = next_node_id
                self.current_node_id = src

            # wait according to the wait time
            yield self.env.process(self.wait(time=wait_time))

    def __transfer_pass(self):
        will_continue = True
        src = self.current_node_id
        while will_continue:
            next_node_id, will_stop, passenger_pick_count, will_continue, wait_time =\
                self.strategy.get_next_transfer_node()

            # stop = self.network.get_node(self.current_node_id)
            # if will_stop:
            #     if passenger_pick_count > 0:
            #         self.strategy.passenger_fill(stop)
            #     self.strategy.passenger_drain(stop)

            if will_continue:
                edge = self.network.get_edge(src, next_node_id)
                yield self.env.process(self.pass_edge(edge=edge,
                                                      pass_time=self.strategy.edge_travarse_time(edge=edge)))
                src = next_node_id
                self.current_node_id = src

            # wait according to the wait time
            yield self.env.process(self.wait(time=wait_time))

    def process(self):
        yield self.dispatcher.global_vehicle_signal

        # first, plan trip
        self.strategy.plan_trip()

        yield self.env.timeout(delay=self.departure_time)
        while self.repeat:
            Logger.log(
                "route {0} vehicle {1} trip_start {2} at {3:.0f}".format(self.route_id, self.id, self.trip_count,
                                                                         self.env.now))
            # do forward pass of trip
            yield self.env.process(self.__forward_pass())
            Logger.log("route {0} vehicle {1} forward_pass_completion at {2:.0f}".format(self.route_id, self.id,
                                                                                         self.env.now))
            # yield self.env.process(self.wait(5))
            # do backward pass of trip
            yield self.env.process(self.__backward_pass())
            Logger.log("route {0} vehicle {1} backward_pass_completion at {2:.0f}".format(self.route_id, self.id,
                                                                                          self.env.now))
            # yield self.env.process(self.wait(5))
            # notify dispatcher about trip completion
            self.dispatcher.notify(self.id)
            self.trip_count += 1
            Logger.log("route {0} vehicle {1} trip_completion {2} at {3:.0f}".format(self.route_id, self.id,
                                                                                     self.trip_count, self.env.now))

            will_transfer, self.repeat = self.dispatcher.update_route(vehicle=self)
            if will_transfer:
                yield self.env.process(self.__transfer_pass())
                Logger.log("route {0} vehicle {1} transfer_pass_completion at {2:.0f}".format(self.route_id, self.id,
                                                                                              self.env.now))
                # trip should be planned again as new route
                self.strategy.plan_trip()

            # yield self.dispatcher_signal
