import re
import matplotlib.pyplot as plot
import copy

from network import Network

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


class SpeedBinContainer:
    def __init__(self, resolution):
        self.resolution = resolution
        self.speed_bin_dict: dict[int, SpeedBin] = {}
        self.vehicle_latest_entry_dict: dict[int, int] = {}

    def set_time_step(self, avg_velocity_time_step_sec: int):
        self.resolution = avg_velocity_time_step_sec

    def vehicle_enter_data_entry(self, vehicle_id: int, entry_time: int):
        self.vehicle_latest_entry_dict[vehicle_id] = entry_time

    def vehicle_leave_data_entry(self, vehicle_id: int, length: int, leave_time: int):
        entry_time = self.vehicle_latest_entry_dict[vehicle_id]
        entry_event_bin = (entry_time//self.resolution) * self.resolution
        leave_event_bin = (leave_time//self.resolution) * self.resolution

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

            portion = ((leave_time - prev_event_bin) / (leave_time - entry_time)) * length
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


class GraphGenerator:
    def __init__(self):
        self.hourly_trip_completion_stat: dict[int, int] = {}
        self.hourly_trip_start_stat: dict[int, int] = {}
        self.hourly_speed_stat: dict[int, float] = {}
        self.speedbin_container = SpeedBinContainer(resolution=VELOCITY_TIME_RESOLUTION_SEC)

    def __analyze_event_log(self, avg_velocity_time_step_sec: int):
        self.speedbin_container.set_time_step(avg_velocity_time_step_sec=avg_velocity_time_step_sec)

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
                elif event_type == "entering":
                    timestamp = int(result.groups()[6])
                    self.speedbin_container.vehicle_enter_data_entry(vehicle_id=vehicle_id, entry_time=timestamp)
                elif event_type == "leaving":
                    length = float(result.groups()[5])
                    timestamp = int(result.groups()[6])
                    self.speedbin_container.vehicle_leave_data_entry(vehicle_id=vehicle_id, length=length,
                                                                     leave_time=timestamp)
                elif event_type == "boarding":
                    pass
                elif event_type == "offloading":
                    pass

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