import simpy
import os
import sys
import importlib.util

from networkprimitive import Edge, Node, Route

INF_CAP = -1


class NetworkEdgeData:
    def __init__(self):
        self.cap_data = []

    def get_cap(self, src_id: int, dst_id: int) -> int:
        return self.cap_data[src_id][dst_id]

    def load_data(self, filepath: str, ):
        self.cap_data = []
        with open(filepath) as fin:
            for line in fin.readlines():
                self.cap_data.append([])

                for token in line.split():
                    # network.txt maybe used as edge capacity data
                    # in network.txt -1 is used to indicate no connection/link not exist
                    # hence it should be zero capacity
                    edge_capacity = float(token)
                    if edge_capacity == -1:
                        edge_capacity = 0
                    self.cap_data[-1].append(edge_capacity)


class NetworkNodeData:
    def __init__(self):
        self.cap_data = []
        self.demand_dict_list = []

    def get_cap(self, node_id: int) -> int:
        return self.cap_data[node_id]

    def get_demand_dict(self, node_id: int) -> dict[int, int]:
        return self.demand_dict_list[node_id]

    def load_data(self, demand_filepath: str, vehicle_capfilepath: str=None):
        self.cap_data = []
        if vehicle_capfilepath is not None:
            with open(vehicle_capfilepath) as fin:
                for line in fin.readlines():
                    self.cap_data.append(int(line))

        self.demand_dict_list = []
        with open(demand_filepath) as fin:
            src_id = 0
            for line in fin.readlines():
                dst_id = 0
                self.demand_dict_list.append({})
                for token in line.split():
                    self.demand_dict_list[src_id][dst_id] = int(token)
                    dst_id += 1
                src_id += 1

        # if no capacity data given assume capacity 1
        if vehicle_capfilepath is None:
            self.cap_data = [1] * len(self.demand_dict_list)


class Network:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.node_data = NetworkNodeData()
        self.edge_cap_data = NetworkEdgeData()
        self.route_list: list[Route] = []
        self.edge_dict: dict[(int, int), Edge] = {}
        self.node_list: list[Node] = []
        self.node_class = Node

    def __load_node_class(self, node_class_full_import_string: str):
        import_data = node_class_full_import_string.split(".")
        module_path = ".".join(import_data[:-1])
        # extract module name by removing .py from basepath
        module_name = ".".join(os.path.basename(module_path).split(".")[:-1])
        class_name = import_data[-1]

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        self.node_class = getattr(module, class_name)

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
                          node_class_script_path: str, network_nodecap_filepath: str=None):
        self.__load_node_class(node_class_full_import_string=node_class_script_path + ".Node")
        self.edge_cap_data.load_data(network_edgecap_filepath)
        self.node_data.load_data(network_demand_filepath, network_nodecap_filepath)

        self.node_list = []
        with open(network_filepath) as fin:
            src_id = 0
            for line in fin.readlines():
                dst_id = 0

                self.node_list.append(self.node_class(node_id=src_id, env=self.env,
                                                      capacity=self.node_data.get_cap(src_id),
                                                      dest_id_passenger_dict=self.node_data.get_demand_dict(src_id)))

                for token in line.split():
                    if float(token) != INF_CAP:
                        self.edge_dict[(src_id, dst_id)] = Edge(src_id, dst_id, self.env, float(token),
                                                                self.edge_cap_data.get_cap(src_id, dst_id))
                    dst_id += 1

                src_id += 1
