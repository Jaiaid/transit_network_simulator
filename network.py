import simpy

from networkprimitive import Edge, Node, Route

INF_CAP = -1


class NetworkEdgeData:
    def __init__(self):
        self.cap_data = []

    def get_cap(self, src_id: int, dst_id: int) -> int:
        return self.cap_data[src_id][dst_id]

    def load_data(self, filepath: str, ):
        with open(filepath) as fin:
            for line in fin.readlines():
                self.cap_data.append([])

                for token in line.split():
                    self.cap_data[-1].append(int(token))


class NetworkNodeData:
    def __init__(self):
        self.cap_data = []
        self.demand_dict_list = []

    def get_cap(self, node_id: int) -> int:
        return self.cap_data[node_id]

    def get_demand_dict(self, node_id: int) -> dict[int, int]:
        return self.demand_dict_list[node_id]

    def load_data(self, demand_filepath: str, vehicle_capfilepath: str):
        with open(vehicle_capfilepath) as fin:
            for line in fin.readlines():
                self.cap_data.append(int(line))

        with open(demand_filepath) as fin:
            src_id = 0
            for line in fin.readlines():
                dst_id = 0
                self.demand_dict_list.append({})
                for token in line.split():
                    self.demand_dict_list[src_id][dst_id] = int(token)
                    dst_id += 1
                src_id += 1


class Network:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.node_data = NetworkNodeData()
        self.edge_cap_data = NetworkEdgeData()
        self.route_list: list[Route] = []
        self.edge_dict: dict[(int, int), Edge] = {}
        self.node_list: list[Node] = []

    def get_route(self, route_id: int):
        return self.route_list[route_id]

    def get_edge(self, src_id: int, dst_id: int) -> Edge:
        return self.edge_dict[(src_id, dst_id)]

    def get_node(self, node_id: int) -> Node:
        return self.node_list[node_id]

    def get_demand(self, node_id: int) -> dict[int, int]:
        return self.node_list[node_id].get_demand_dict()

    def load_route_data(self, network_route_filepath: str):
        with open(network_route_filepath) as fin:
            route_id = 0
            for line in fin.readlines():
                route_node_list = []
                for token in line.split():
                    route_node_list.append(int(token))
                self.route_list.append(Route(route_id=route_id, route_node_list=route_node_list))
                route_id += 1

    def load_network_data(self, network_filepath: str, network_edgecap_filepath: str, network_demand_filepath: str,
                          network_nodecap_filepath: str):
        self.edge_cap_data.load_data(network_edgecap_filepath)
        self.node_data.load_data(network_demand_filepath, network_nodecap_filepath)

        with open(network_filepath) as fin:
            src_id = 0
            for line in fin.readlines():
                dst_id = 0

                self.node_list.append(Node(node_id=src_id, env=self.env, capacity=self.node_data.get_cap(src_id),
                                           dest_id_passenger_dict=self.node_data.get_demand_dict(src_id)))

                for token in line.split():
                    if float(token) != INF_CAP:
                        self.edge_dict[(src_id, dst_id)] = Edge(src_id, dst_id, self.env, float(token),
                                                                self.edge_cap_data.get_cap(src_id, dst_id))
                    dst_id += 1

                src_id += 1
