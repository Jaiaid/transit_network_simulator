import simpy

from logger import Logger


class Edge(simpy.Container):
    def __len__(self):
        return self.length

    def __init__(self, src_id: int, dst_id: int, env: simpy.Environment, length: float, capacity: int):
        self.length = length
        self.src_id = src_id
        self.dst_id = dst_id
        self.env = env
        super().__init__(env, max(capacity, 1))


class Node(simpy.Resource):
    def __init__(self, node_id: int, env: simpy.Environment, capacity: int, dest_id_passenger_dict: dict[int, int]):
        self.id = node_id
        self.dest_id_passenger_dict = dest_id_passenger_dict
        self.env = env
        super().__init__(env, capacity)

    def drain(self, route_id: int, vehicle_id: int, dest_id: int, count: int) -> int:
        if dest_id in self.dest_id_passenger_dict:
            boarding = min(count, self.dest_id_passenger_dict[dest_id])
            Logger.log(
                "route {0} vehicle {1} boarding {2} passenger for {3} from {4} at {5}".format(
                    route_id, vehicle_id, boarding, dest_id, self.id, self.env.now)
            )
            self.dest_id_passenger_dict[dest_id] -= boarding

            return 0

    def fill(self, dest_id_passenger_inc_dict: dict[int, int]):
        pass

    def get_demand_to(self, dest_id):
        if dest_id in self.dest_id_passenger_dict:
            return self.dest_id_passenger_dict[dest_id]
        return 0


class Route:
    def __init__(self, route_id: int, route_node_list: list[int]):
        self.id = route_id
        self.route_node_list = route_node_list
