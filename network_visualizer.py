import time
import simpy
import re
import argparse
from pyvis.network import Network as NetworkDrawingObject

from network import Network
from fleet import Fleet


DATA_FILE_NAME = "event_log.txt"

REGEX_VEHICLE_EVENT_LINE_TYPE3 = \
    r"^route (\d+) vehicle (\d+) ([a-z_]+) edge (\d+),(\d+) of length (\d+\.?\d*) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE4 = \
    r"^route (\d+) vehicle (\d+) ([a-z_]+) (\d+) passenger for (\d+) from (\d+) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE5 = r"^route (\d+) vehicle (\d+) ([a-z_]+) (\d+) passenger for (\d+) at (\d+\.?\d*)"

DEFAULT_TIME_STEP = 600


class EdgeVehicleBin:
    def __init__(self):
        self.edge_id_to_holding_dict: dict[int, float] = {}

    def add_holding(self, edge_id: int, length: float):
        if edge_id not in self.edge_id_to_holding_dict:
            self.edge_id_to_holding_dict[edge_id] = 0
        self.edge_id_to_holding_dict[edge_id] += length

    def remove_holding(self, edge_id: int, length: float):
        if edge_id not in self.edge_id_to_holding_dict:
            self.edge_id_to_holding_dict[edge_id] = 0
        self.edge_id_to_holding_dict[edge_id] -= length

    def get_holding(self, edge_id: int) -> float:
        if edge_id not in self.edge_id_to_holding_dict:
            return 0
        return self.edge_id_to_holding_dict[edge_id]


class EdgeVehicleBinContainer:
    def __init__(self, resolution):
        self.resolution = resolution
        self.edge_count_bin_dict: dict[int, EdgeVehicleBin] = {}
        self.sorted_timebin = []

    def __binary_search_nearest_timebin(self, timebin: int):
        f_indx = 0
        l_indx = len(self.sorted_timebin)
        m_indx = int((f_indx + l_indx) // 2)

        while f_indx <= l_indx:
            if self.sorted_timebin[m_indx] < timebin:
                f_indx = m_indx + 1
            elif self.sorted_timebin[m_indx] > timebin:
                l_indx = m_indx - 1
            else:
                return self.sorted_timebin[m_indx]

        if abs(self.sorted_timebin[f_indx] - timebin) < abs(self.sorted_timebin[l_indx] - timebin):
            return self.sorted_timebin[f_indx]
        return self.sorted_timebin[l_indx]

    def set_time_step(self, timestep_sec: int):
        self.resolution = timestep_sec

    def vehicle_enter_data_entry(self, edge_id: int, vehicle_length: float, entry_time: int):
        entry_event_bin = (entry_time // self.resolution) * self.resolution
        if entry_event_bin not in self.edge_count_bin_dict:
            self.edge_count_bin_dict[entry_event_bin] = EdgeVehicleBin()
        self.edge_count_bin_dict[entry_event_bin].add_holding(edge_id=edge_id, length=vehicle_length)

    def vehicle_leave_data_entry(self, edge_id: int, vehicle_length: float, leave_time: int):
        leave_event_bin = (leave_time // self.resolution) * self.resolution
        if leave_event_bin not in self.edge_count_bin_dict:
            self.edge_count_bin_dict[leave_event_bin] = EdgeVehicleBin()
        self.edge_count_bin_dict[leave_event_bin].remove_holding(edge_id=edge_id, length=vehicle_length)

    def get_edge_holding(self, timestamp_sec: int):
        event_bin = (timestamp_sec // self.resolution) * self.resolution
        # if not in find the nearest event bin
        if event_bin not in self.edge_count_bin_dict:
            if len(self.sorted_timebin) == 0:
                # first get the keys/timebins
                # then sort to do binary search later
                self.sorted_timebin = list(self.edge_count_bin_dict.keys())
                self.sorted_timebin.sort()
            return self.edge_count_bin_dict[self.__binary_search_nearest_timebin(timebin=event_bin)]
        return self.edge_count_bin_dict[event_bin]


class NetworkVisualizer:
    def __init__(self, network: Network, fleet: Fleet):
        self.network: Network = network
        self.fleet: Fleet = fleet
        self.drawn_network = NetworkDrawingObject()
        self.added_edge_count = 0
        self.edge_tuple_to_id_dict = {}
        self.edge_count_container = EdgeVehicleBinContainer(resolution=DEFAULT_TIME_STEP)

    def set_time_setp(self, timestep_sec):
        self.edge_count_container.set_time_step(timestep_sec=timestep_sec)

    def __init_internal(self):
        self.added_edge_count = 0
        for edge_src_dst_tuple, edge in self.network.edge_dict.items():
            if edge_src_dst_tuple not in self.edge_tuple_to_id_dict:
                self.edge_tuple_to_id_dict[edge_src_dst_tuple] = self.added_edge_count
                self.added_edge_count += 1

    def __analyze_event_log(self, timestep_sec: int):
        self.set_time_setp(timestep_sec=timestep_sec)

        with open(DATA_FILE_NAME) as log_fin:
            for logline in log_fin.readlines():
                logline = logline.split('\n')[0]

                result = re.search(REGEX_VEHICLE_EVENT_LINE_TYPE3, logline)
                if result is None:
                    result = re.search(REGEX_VEHICLE_EVENT_LINE_TYPE3, logline)
                if result is None:
                    result = re.search(REGEX_VEHICLE_EVENT_LINE_TYPE4, logline)
                if result is None:
                    result = re.search(REGEX_VEHICLE_EVENT_LINE_TYPE5, logline)
                if result is None:
                    continue

                route_id = int(result.groups()[0])
                vehicle_id = int(result.groups()[1])
                event_type = result.groups()[2]

                if event_type == "entering":
                    timestamp = int(float(result.groups()[6]))
                    src_id = int(result.groups()[3])
                    dst_id = int(result.groups()[4])
                    edge = self.network.get_edge(src_id=src_id, dst_id=dst_id)

                    edge_id = self.edge_tuple_to_id_dict[(src_id, dst_id)]

                    self.edge_count_container.vehicle_enter_data_entry(
                        edge_id=edge_id, vehicle_length=self.fleet.vehicle_dict[vehicle_id].length, entry_time=timestamp
                    )
                elif event_type == "leaving":
                    timestamp = int(float(result.groups()[6]))
                    src_id = int(result.groups()[3])
                    dst_id = int(result.groups()[4])
                    edge = self.network.get_edge(src_id=src_id, dst_id=dst_id)

                    edge_id = self.edge_tuple_to_id_dict[(src_id, dst_id)]
                    self.edge_count_container.vehicle_leave_data_entry(
                        edge_id=edge_id, vehicle_length=self.fleet.vehicle_dict[vehicle_id].length, leave_time=timestamp
                    )

    def draw_network_view(self):
        # first draw the nodes
        node_id_list = [node.id for node in self.network.node_list]
        node_label_list = [str(node.id) for node in self.network.node_list]
        self.drawn_network.add_nodes(nodes=node_id_list, label = node_label_list)
        # then add edges
        for edge_src_dst_tuple, edge in self.network.edge_dict.items():
            self.drawn_network.add_edge(source=edge_src_dst_tuple[0], to=edge_src_dst_tuple[1], value=1)
        # property set
        self.drawn_network.repulsion(damping=100)
        # self.drawn_network.toggle_physics(status=False)
        # then show
        self.drawn_network.show("transit_network.html")

    def update_network_view(self, update_timebin: int):
        # first get holding data for the timebin
        holding_data = self.edge_count_container.get_edge_holding(timestamp_sec=update_timebin)
        # update the edges
        for edge_src_dst_tuple, edge in self.network.edge_dict.items():
            holding = holding_data.get_holding(edge_id=self.edge_tuple_to_id_dict[edge_src_dst_tuple])
            capacity = self.network.edge_cap_data.get_cap(src_id=edge_src_dst_tuple[0], dst_id=edge_src_dst_tuple[1])

            if capacity == 0:
                self.drawn_network.add_edge(source=edge_src_dst_tuple[0], to=edge_src_dst_tuple[1], value=0)
            else:
                self.drawn_network.add_edge(
                    source=edge_src_dst_tuple[0], to=edge_src_dst_tuple[1], value=holding/capacity)

    def render_network(self, timestep_sec: int, duration: int):
        self.__init_internal()
        self.__analyze_event_log(timestep_sec=timestep_sec)

        # first draw
        self.draw_network_view()
        for timebin in range(0, duration, timestep_sec):
            time.sleep(0.01)
            self.update_network_view(update_timebin=timebin)


if __name__=="__main__":
    # edit file path here to change data source
    parser = argparse.ArgumentParser()
    parser.add_argument("-dir", "--input_dir", help="folder path containing the input files", required=True)
    parser.add_argument("-elog", "--event_log", help="event log containing data on vehicle in an edge", required=True)
    parser.add_argument("-ts", "--time_step", help="time step used in generate data point for graphs", type=int,
                        default=600, required=False)
    parser.add_argument("-dur", "--duration", help="graph will be simulated for how many in simulator second", type=int,
                        default=21600, required=False)
    # get cmd line arguments
    args = parser.parse_args()

    nodecap_filepath = "{0}/stopcap.txt".format(args.input_dir)
    edgecap_filepath = "{0}/edgecap.txt".format(args.input_dir)
    network_filepath = "{0}/network.txt".format(args.input_dir)
    demand_filepath = "{0}/demand.txt".format(args.input_dir)
    fleet_filepath = "{0}/fleet.txt".format(args.input_dir)

    # not needed, just to reuse already implemented Network and Fleet object
    env = simpy.Environment()
    # load network data
    network: Network = Network(env=env)
    network.load_network_data(network_filepath=network_filepath, network_demand_filepath=demand_filepath,
                              network_edgecap_filepath=edgecap_filepath, network_nodecap_filepath=nodecap_filepath)

    fleet: Fleet = Fleet(env=env)
    fleet.load_data(filepath=fleet_filepath)

    network_visualizer = NetworkVisualizer(network=network, fleet=fleet)
    network_visualizer.render_network(timestep_sec=args.time_step, duration=args.duration)