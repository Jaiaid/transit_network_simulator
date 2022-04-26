import simpy


class Edge(simpy.Resource):
    def __len__(self):
        return self.length

    def __init__(self, src_id: int, dst_id: int, env: simpy.Environment, length: int, capacity: int):
        self.length = length
        self.src_id = src_id
        self.dst_id = dst_id
        super().__init__(env, capacity)


class Node(simpy.Resource):
    def __init__(self, node_id: int, env: simpy.Environment, capacity: int, dest_id_passenger_dict: dict[int, int]):
        self.id = node_id
        self.dest_id_passenger_dict = dest_id_passenger_dict
        super().__init__(env, capacity)


class Route:
    def __init__(self, route_id: int, route_node_list: list[int]):
        self.id = route_id
        self.route_node_list = route_node_list
