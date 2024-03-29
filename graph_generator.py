import re
import matplotlib.pyplot as plot

DATA_FILE_NAME = "event_log.txt"

REGEX_VEHICLE_EVENT_LINE_TYPE1 = r"^route (\d+) vehicle (\d+) ([a-z_]+) (\d+) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE2 = r"^route (\d+) vehicle (\d+) ([a-z_]+) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE3 = \
    r"^route (\d+) vehicle (\d+) ([a-z_]+) edge (\d+),(\d+) of length (\d+\.?\d*) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE4 = \
    r"^route (\d+) vehicle (\d+) ([a-z_]+) (\d+) passenger for (\d+) from (\d+) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE5 = r"^route (\d+) vehicle (\d+) ([a-z_]+) (\d+) passenger for (\d+) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE6 = r"^total vehicle (\d+) at (\d+\.?\d*)"

VELOCITY_TIME_RESOLUTION_SEC = 600
PASSENGER_TRANSFER_RESOLUTION_SEC = 600

REGEX_WAITTIME = r"^Waiting time: (\d*\.\d+)"
REGEX_EVACTIME = r"^Total Evacuation Time: (\d*\.\d+)"
REGEX_TRIPCOUNT = r"^Number of trips: (\d+)"
REGEX_EVACUEECOUNT = r"^Number of evacuaees: (\d+)"
REGEX_RESULT_FILENAME = r"result(\d+).txt"


class SpeedBin:
    def __init__(self):
        self.total_travel_length = 0
        self.running_vehicle_id_dict = {}

    def add_travel_length(self, vehicle_id: int, length: float):
        self.total_travel_length += length
        if vehicle_id not in self.running_vehicle_id_dict:
            self.running_vehicle_id_dict[vehicle_id] = 0
        self.running_vehicle_id_dict[vehicle_id] += 1

    def get_mean(self, timestep: float) -> float:
        if len(self.running_vehicle_id_dict.keys()) > 0:
            return self.total_travel_length / (len(self.running_vehicle_id_dict.keys()) * timestep)
        return 0


class PopulationBin:
    def __init__(self):
        self.total_transfer = 0
        self.running_vehicle_id_dict = {}

    def add_transfer(self, vehicle_id: int, count: int):
        self.total_transfer += count
        if vehicle_id not in self.running_vehicle_id_dict:
            self.running_vehicle_id_dict[vehicle_id] = 0
        self.running_vehicle_id_dict[vehicle_id] += 1

    def get_transfer(self) -> int:
        return self.total_transfer


class SpeedBinContainer:
    def __init__(self, resolution):
        self.resolution = resolution
        self.speed_bin_dict: dict[int, SpeedBin] = {}
        self.vehicle_latest_entry_dict: dict[int, float] = {}

    def set_time_step(self, avg_velocity_time_step_sec: int):
        self.resolution = avg_velocity_time_step_sec

    def vehicle_enter_data_entry(self, vehicle_id: int, entry_time: float):
        self.vehicle_latest_entry_dict[vehicle_id] = entry_time

    def vehicle_leave_data_entry(self, vehicle_id: int, length: float, leave_time: float):
        entry_time = self.vehicle_latest_entry_dict[vehicle_id]
        entry_event_bin = (int(entry_time//self.resolution)) * self.resolution
        leave_event_bin = (int(leave_time//self.resolution)) * self.resolution

        if entry_event_bin == leave_event_bin:
            if entry_event_bin not in self.speed_bin_dict:
                self.speed_bin_dict[entry_event_bin] = SpeedBin()
            self.speed_bin_dict[entry_event_bin].add_travel_length(vehicle_id=vehicle_id, length=length)
        else:
            for event_bin in range(entry_event_bin, leave_event_bin, self.resolution):
                if event_bin not in self.speed_bin_dict:
                    self.speed_bin_dict[entry_event_bin] = SpeedBin()

            if leave_event_bin not in self.speed_bin_dict:
                self.speed_bin_dict[leave_event_bin] = SpeedBin()

            # add the first portion of traveled length (length traveled in first bin)
            portion = ((entry_event_bin + self.resolution - entry_time) / (leave_time - entry_time)) * length
            self.speed_bin_dict[entry_event_bin].add_travel_length(vehicle_id=vehicle_id, length=portion)

            prev_time = entry_time
            prev_event_bin = entry_event_bin
            for event_bin in range(entry_event_bin + self.resolution, leave_event_bin,
                                   self.resolution):
                portion = ((event_bin - prev_time) / (leave_time - entry_time)) * length

                if prev_event_bin not in self.speed_bin_dict:
                    self.speed_bin_dict[prev_event_bin] = SpeedBin()

                self.speed_bin_dict[prev_event_bin].add_travel_length(vehicle_id=vehicle_id, length=portion)
                prev_event_bin = event_bin
                prev_time = event_bin

            # add the last portion of traveled length (length traveled in last bin)
            portion = ((leave_time - leave_event_bin) / (leave_time - entry_time)) * length
            self.speed_bin_dict[leave_event_bin].add_travel_length(vehicle_id=vehicle_id, length=portion)

    def generate_graph(self):
        fig_avg_speed, ax_avg_speed = plot.subplots()

        x_coords = sorted(list(self.speed_bin_dict.keys()))
        y_coords = []
        for x in x_coords:
            y_coords.append(self.speed_bin_dict[x].get_mean(timestep=self.resolution))

        ax_avg_speed.plot(x_coords, y_coords)
        ax_avg_speed.set_title("average velocity in {0}s resolution".format(self.resolution))
        ax_avg_speed.legend()
        ax_avg_speed.set_xlabel("second")
        ax_avg_speed.set_ylabel("unit/sec")
        fig_avg_speed.savefig("average_velocity.png", dpi=300)


class PopulationBinContainer:
    def __init__(self, resolution):
        self.resolution = resolution
        self.population_bin_dict: dict[int, PopulationBin] = {}
        self.vehicle_latest_entry_dict: dict[int, int] = {}

    def set_time_step(self, transfer_bin_time_step_sec: int):
        self.resolution = transfer_bin_time_step_sec

    def passenger_reaching_data_entry(self, vehicle_id: int, count: int, leave_time: int):
        leave_event_bin = (leave_time // self.resolution) * self.resolution
        if leave_event_bin not in self.population_bin_dict:
            self.population_bin_dict[leave_event_bin] = PopulationBin()
        self.population_bin_dict[leave_event_bin].add_transfer(vehicle_id=vehicle_id, count=count)

    def generate_graph(self, barplot: bool = True):
        x_coords = sorted(list(self.population_bin_dict.keys()))
        presented_x_coords = []
        y_coords = []

        fig_avg_speed, ax_avg_transfer_complete = plot.subplots()

        if barplot:
            for x in x_coords:
                if self.population_bin_dict[x].get_transfer() > 0:
                    y_coords.append(self.population_bin_dict[x].get_transfer())
                    presented_x_coords.append(int(x//3600))

            ax_avg_transfer_complete.bar([str(hr) for hr in presented_x_coords], y_coords, color='maroon', width=0.4)
            ax_avg_transfer_complete.set_title("transfer completion per hour".format(self.resolution))
            ax_avg_transfer_complete.legend()
            ax_avg_transfer_complete.set_xlabel("hour")
            ax_avg_transfer_complete.set_ylabel("person")
            fig_avg_speed.savefig("hourly_transfer_completion_barplot.png", dpi=300)
        else:
            presented_x_coords = []
            for x in x_coords:
                if self.population_bin_dict[x].get_transfer() > 0:
                    y_coords.append(self.population_bin_dict[x].get_transfer())
                    presented_x_coords.append(x)

            ax_avg_transfer_complete.plot(presented_x_coords, y_coords)
            ax_avg_transfer_complete.set_title("transfer completion in {0}s resolution".format(self.resolution))
            ax_avg_transfer_complete.legend()
            ax_avg_transfer_complete.set_xlabel("seconds")
            ax_avg_transfer_complete.set_ylabel("person")
            fig_avg_speed.savefig("hourly_transfer_completion_plot.png", dpi=300)


class GraphGenerator:
    def __init__(self):
        self.hourly_trip_completion_stat: dict[int, int] = {}
        self.hourly_trip_start_stat: dict[int, int] = {}
        self.hourly_speed_stat: dict[int, float] = {}
        self.speedbin_container = SpeedBinContainer(resolution=VELOCITY_TIME_RESOLUTION_SEC)
        self.populationbin_container = PopulationBinContainer(resolution=PASSENGER_TRANSFER_RESOLUTION_SEC)
        self.hourly_populationbin_container = PopulationBinContainer(resolution=PASSENGER_TRANSFER_RESOLUTION_SEC)

        # some status variable to store update after each analysis
        # passenger related
        self.__last_passenger_offload_time = None
        self.__last_passenger_offload_node_id = None
        self.__last_passenger_offload_vehicle_id = None
        self.__last_passenger_offload_route_id = None
        self.__total_served_passenger = 0
        # trip completion related
        self.__last_trip_completion_time = None
        self.__last_trip_completion_route_id = None
        self.__last_trip_completion_vehicle_id = None

    def __reset(self):
        # reset the variable which will be updated after each analysis
        self.__last_passenger_offload_time = None
        self.__last_passenger_offload_node_id = None
        self.__last_passenger_offload_vehicle_id = None
        self.__last_passenger_offload_route_id = None
        self.__total_served_passenger = 0

        self.__last_trip_completion_time = None
        self.__last_trip_completion_route_id = None
        self.__last_trip_completion_vehicle_id = None

    def __analyze_event_log(self, avg_velocity_time_step_sec: int):
        # reset the internally stored analysis data
        self.__reset()

        self.speedbin_container.set_time_step(avg_velocity_time_step_sec=avg_velocity_time_step_sec)
        # for now we are only generating per hour transfer completion bar plot
        self.hourly_populationbin_container.set_time_step(transfer_bin_time_step_sec=3600)
        self.populationbin_container.set_time_step(transfer_bin_time_step_sec=avg_velocity_time_step_sec)

        with open(DATA_FILE_NAME) as log_fin:
            for logline in log_fin.readlines():
                logline = logline.split('\n')[0]

                result = re.search(REGEX_VEHICLE_EVENT_LINE_TYPE1, logline)
                if result is None:
                    result = re.search(REGEX_VEHICLE_EVENT_LINE_TYPE2, logline)
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

                if event_type == "trip_start":
                    timestamp = float(result.groups()[4])
                    # hourly, hence 3600
                    hour = int(timestamp // 3600)
                    if hour not in self.hourly_trip_start_stat:
                        self.hourly_trip_start_stat[hour] = 1
                    else:
                        self.hourly_trip_start_stat[hour] += 1
                elif event_type == "trip_completion":
                    timestamp = float(result.groups()[4])
                    # hourly, hence 3600
                    hour = int(timestamp // 3600)
                    if hour not in self.hourly_trip_completion_stat:
                        self.hourly_trip_completion_stat[hour] = 0
                    self.hourly_trip_completion_stat[hour] += 1

                    self.__last_trip_completion_time = timestamp
                    self.__last_trip_completion_route_id = route_id
                    self.__last_trip_completion_vehicle_id = vehicle_id
                elif event_type == "entering":
                    timestamp = float(result.groups()[6])
                    self.speedbin_container.vehicle_enter_data_entry(vehicle_id=vehicle_id, entry_time=timestamp)
                elif event_type == "leaving":
                    length = float(result.groups()[5])
                    timestamp = float(result.groups()[6])
                    self.speedbin_container.vehicle_leave_data_entry(vehicle_id=vehicle_id, length=length,
                                                                     leave_time=timestamp)
                elif event_type == "boarding":
                    pass
                elif event_type == "offloading":
                    count = int(result.groups()[3])
                    offloading_node_id = int(result.groups()[4])
                    timestamp = int(float(result.groups()[5]))

                    self.populationbin_container.passenger_reaching_data_entry(vehicle_id=vehicle_id, count=count,
                                                                               leave_time=timestamp)
                    self.hourly_populationbin_container.passenger_reaching_data_entry(
                        vehicle_id=vehicle_id, count=count, leave_time=timestamp)

                    self.__last_passenger_offload_time = timestamp
                    self.__last_passenger_offload_vehicle_id = vehicle_id
                    self.__last_passenger_offload_node_id = offloading_node_id
                    self.__last_passenger_offload_route_id = route_id
                    self.__total_served_passenger += count

    def get_total_served_passenger(self) -> int:
        return self.__total_served_passenger

    def get_last_passenger_served_data(self) -> (int, int, int, int):
        return self.__last_passenger_offload_time, self.__last_passenger_offload_vehicle_id,\
               self.__last_passenger_offload_node_id, self.__last_passenger_offload_route_id

    def get_last_trip_completion_data(self) -> (int, int, int):
        return self.__last_trip_completion_time, self.__last_trip_completion_vehicle_id,\
               self.__last_trip_completion_route_id

    def generate(self, avg_velocity_time_step_sec: int):
        self.__analyze_event_log(avg_velocity_time_step_sec=avg_velocity_time_step_sec)

        fig_trip_start, ax_trip_start = plot.subplots()
        fig_trip_complete, ax_trip_complete = plot.subplots()

        ax_trip_start.bar([str(key) for key in self.hourly_trip_start_stat.keys()],
                          list(self.hourly_trip_start_stat.values()), color='maroon', width=0.4)
        ax_trip_complete.bar([str(key) for key in self.hourly_trip_completion_stat.keys()],
                             list(self.hourly_trip_completion_stat.values()), color='maroon', width=0.4)

        ax_trip_start.set_title("trip start hourly count")
        ax_trip_start.legend()
        ax_trip_start.set_xlabel("hour")
        ax_trip_start.set_ylabel("count")
        fig_trip_start.savefig("hourly_trip_start_barplot.png", dpi=300)

        ax_trip_complete.set_title("trip completion hourly count")
        ax_trip_complete.legend()
        ax_trip_complete.set_xlabel("hour")
        ax_trip_complete.set_ylabel("count")
        fig_trip_complete.savefig("hourly_trip_completion_barplot.png", dpi=300)

        self.speedbin_container.generate_graph()
        self.hourly_populationbin_container.generate_graph(barplot=True)
        self.populationbin_container.generate_graph(barplot=False)
