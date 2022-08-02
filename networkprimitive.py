import simpy


class Edge(simpy.Container):
    def __len__(self):
        return self.length

    def __init__(self, src_id: int, dst_id: int, env: simpy.Environment, length: float, capacity: int):
        self.length = length
        self.src_id = src_id
        self.dst_id = dst_id
        self.env = env
        super().__init__(env, max(capacity, 1))


class Route:
    def __init__(self, route_id: int, route_node_list: list[int]):
        self.id = route_id
        self.route_node_list = route_node_list
