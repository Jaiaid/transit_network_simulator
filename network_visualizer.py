import math
import time
# unnecessary import to avoid pyinstaller exe error
# numpy' has no attribute '_NoValue
import numpy as np
import simpy
import re
import argparse
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.animation as anime

from network import Network
from fleet import Fleet


DATA_FILE_NAME = "event_log.txt"

REGEX_VEHICLE_EVENT_LINE_TYPE3 = \
    r"^route (\d+) vehicle (\d+) ([a-z_]+) edge (\d+),(\d+) of length (\d+\.?\d*) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE4 = \
    r"^route (\d+) vehicle (\d+) ([a-z_]+) (\d+) passenger for (\d+) from (\d+) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE5 = r"^route (\d+) vehicle (\d+) ([a-z_]+) (\d+) passenger for (\d+) at (\d+\.?\d*)"

DEFAULT_TIME_STEP = 600

# holder of network visualizer
# global object created to use in callback
network_visualizer = None
# global time step holder
time_step = DEFAULT_TIME_STEP


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

        self.added_edge_count = 0
        self.edge_tuple_to_id_dict = {}
        self.edge_count_container = EdgeVehicleBinContainer(resolution=DEFAULT_TIME_STEP)

        self.drawn_network = nx.DiGraph()
        self.network_layout = None
        self.fig, self.ax = plt.subplots()
        self.animation_object = None
        # stored rather than generate each time graph is redrawn
        self.edgekey_list = []

    def set_time_setp(self, timestep_sec):
        self.edge_count_container.set_time_step(timestep_sec=timestep_sec)

    def __init_internal(self):
        self.added_edge_count = 0
        for edge_src_dst_tuple, edge in self.network.edge_dict.items():
            if edge_src_dst_tuple not in self.edge_tuple_to_id_dict:
                self.edge_tuple_to_id_dict[edge_src_dst_tuple] = self.added_edge_count
                self.added_edge_count += 1

    def __analyze_event_log(self, event_log_filepath: str, timestep_sec: int):
        self.set_time_setp(timestep_sec=timestep_sec)

        with open(event_log_filepath) as log_fin:
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
        self.fig.set_tight_layout(True)
        # add edges, node will be added from the edge key list
        self.edgekey_list = []
        for edge_src_dst_tuple, edge in self.network.edge_dict.items():
            # avoid self loop
            if edge_src_dst_tuple[0] != edge_src_dst_tuple[1]:
                self.edgekey_list.append(edge_src_dst_tuple)
            # self.drawn_network.add_edge(source=edge_src_dst_tuple[0], to=edge_src_dst_tuple[1], value=1)
        # add edges
        self.drawn_network.add_edges_from(self.edgekey_list)
        # set the layout
        self.network_layout = nx.spring_layout(self.drawn_network)

        # value for nodes
        val_map = {'A': 1.0,
                   'D': 0.5714285714285714,
                   'H': 0.0}
        values = [val_map.get(node, 0.25) for node in self.drawn_network.nodes()]

        # draw nodes
        nx.draw_networkx_nodes(self.drawn_network, self.network_layout, ax=self.ax, cmap=plt.get_cmap('jet'),
                               node_color=values, node_size=100)
        # draw label
        nx.draw_networkx_labels(self.drawn_network, self.network_layout, ax=self.ax, font_size=5)
        # draw edges, all edges are green color at first
        nx.draw_networkx_edges(self.drawn_network, self.network_layout, ax=self.ax, edgelist=self.edgekey_list,
                               edge_color=(0, 1, 0), arrows=False)

    def update_network_view(self, update_timebin: int):
        print("current time : {0}".format(update_timebin), end="\r")
        # 50ms sleep, otherwise too fast update
        time.sleep(0.05)
        self.ax.clear()
        # first get holding data for the timebin
        holding_data = self.edge_count_container.get_edge_holding(timestamp_sec=update_timebin)
        # update the edges
        edge_color_list = []
        for edge_src_dst_tuple, edge in self.network.edge_dict.items():
            holding = holding_data.get_holding(edge_id=self.edge_tuple_to_id_dict[edge_src_dst_tuple])
            capacity = self.network.edge_cap_data.get_cap(src_id=edge_src_dst_tuple[0], dst_id=edge_src_dst_tuple[1])
            # TODO
            # do something about self edges and capacity zero edges
            if capacity == 0:
                edge_color_list.append((1.0, 1.0, 1.0))
            else:
                edge_color_list.append((holding/capacity, 1-holding/capacity, 0))

        # add the edges
        self.drawn_network.add_edges_from(self.edgekey_list)
        # value for nodes
        val_map = {'A': 1.0,
                   'D': 0.5714285714285714,
                   'H': 0.0}
        values = [val_map.get(node, 0.25) for node in self.drawn_network.nodes()]
        # draw nodes
        nx.draw_networkx_nodes(self.drawn_network, self.network_layout, ax=self.ax, cmap=plt.get_cmap('jet'),
                               node_color=values, node_size=100)
        # draw label
        nx.draw_networkx_labels(self.drawn_network, self.network_layout, ax=self.ax, font_size=5)
        # draw edges, all edges are green color at first
        nx.draw_networkx_edges(self.drawn_network, self.network_layout, ax=self.ax, edgelist=self.edgekey_list,
                               edge_color=edge_color_list, arrows=False)

    def render_network(self, event_log_file_path: str, timestep_sec: int, duration: int):
        self.__init_internal()
        self.__analyze_event_log(event_log_filepath=event_log_file_path, timestep_sec=timestep_sec)

        # first draw
        self.draw_network_view()
        # initialize animation object
        # the object is stored to avoid garbage collection of it (according to method doc)
        # number of frame calculated from duration of visualization and timestep used in each frame
        self.animation_object = anime.FuncAnimation(self.fig, animate,
                                                    frames=math.ceil(duration/timestep_sec), repeat=False)

        # now show
        plt.get_current_fig_manager().window.showMaximized()
        plt.show()


def animate(frame_no: int):
    global network_visualizer, time_step
    network_visualizer.update_network_view(update_timebin=frame_no*time_step)


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
    time_step = args.time_step
    network_visualizer.render_network(event_log_file_path=args.event_log,
                                      timestep_sec=args.time_step, duration=args.duration)
