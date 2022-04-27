import simpy

import networkprimitive
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
        self.env = env
        self.dispatcher_signal = self.env.event()
        self.network: Network = None
        self.route_id: int = None
        self.dispatcher = None
        self.strategy = None
        self.repeat = True

    def set_strategy(self, dispatcher, strategy_class: type.__class__):
        self.dispatcher = dispatcher
        self.strategy = strategy_class(self.env, self.dispatcher, self)

    def enter(self, edge, pass_time: int):
        with edge.request() as req:
            yield req
            Logger.log("route {0} vehicle {1} entering edge {2},{3} at {4}".format(self.route_id, self.id,
                                                                                    edge.src_id, edge.dst_id,
                                                                                    self.env.now))
            yield self.env.timeout(pass_time)
            Logger.log("route {0} vehicle {1} leaving edge {2},{3} at {4}".format(self.route_id, self.id,
                                                                                   edge.src_id, edge.dst_id,
                                                                                   self.env.now))

    def leave(self):
        pass

    def wait(self, time: float):
        Logger.log("route {0} vehicle {1} waiting start at {1}".format(self.route_id, self.id, self.env.now))
        yield self.env.timeout(time)
        Logger.log("vehicle {0} waiting finish at {1}".format(self.route_id, self.id, self.env.now))

    def assign_network(self, network: Network):
        self.network = network

    def passenger_in(self, dest_id_passenger_dict: dict[int, int]):
        for stop_id in dest_id_passenger_dict:
            self.passenger_count += dest_id_passenger_dict[stop_id]
            if stop_id in self.dest_id_passenger_dict:
                self.dest_id_passenger_dict[stop_id] += dest_id_passenger_dict[stop_id]
            else:
                self.dest_id_passenger_dict[stop_id] = dest_id_passenger_dict[stop_id]

    def passenger_in_single_dest(self, dest_id: int, count: int) -> int:
        if dest_id not in self.dest_id_passenger_dict:
            self.dest_id_passenger_dict[dest_id] = 0
        if self.passenger_count + count > self.capacity:
            remaining = count - (self.capacity - self.passenger_count)
        else:
            remaining = 0
        self.dest_id_passenger_dict[dest_id] += count - remaining
        return count - remaining

    def passenger_out(self, stop_id: int):
        if stop_id in self.dest_id_passenger_dict:
            self.passenger_count -= self.dest_id_passenger_dict[stop_id]
            Logger.log(
                "route {0} vehicle {1} offloading {2} passenger for {3} at {4}".format(
                    self.route_id, self.id, self.dest_id_passenger_dict[stop_id], stop_id, self.env.now)
            )
            self.dest_id_passenger_dict[stop_id] = 0

    def process(self):
        yield self.dispatcher.global_vehicle_signal
        while self.repeat:
            # first plan trip
            self.strategy.plan_trip()
            Logger.log(
                "route {0} vehicle {1} trip_start {2} at {3}".format(self.route_id, self.id, self.trip_count,
                                                                     self.env.now))
            # do forward pass of trip
            yield self.env.process(self.strategy.forward_pass())
            Logger.log("route {0} vehicle {1} forward_pass_completion at {2}".format(self.route_id, self.id,
                                                                                     self.env.now))
            yield self.env.process(self.wait(5))
            # do backward pass of trip
            yield self.env.process(self.strategy.backward_pass())
            Logger.log("route {0} vehicle {1} backward_pass_completion at {2}".format(self.route_id, self.id,
                                                                                      self.env.now))
            yield self.env.process(self.wait(5))
            # notify dispatcher about trip completion
            self.dispatcher.notify(self.id)
            self.trip_count += 1
            Logger.log("route {0} vehicle {1} trip_completion {2} at {3}".format(self.route_id, self.id,
                                                                                 self.trip_count, self.env.now))
            yield self.dispatcher_signal
